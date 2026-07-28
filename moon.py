import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import os
from flask import Flask
import threading

# ===== ТОКЕН ИЗ ПЕРЕМЕННЫХ ОКРУЖЕНИЯ =====
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = 1396600495552069632
CATEGORY_ID = 1396600496311238793
SUPPORT_ROLE_ID = 1396600495552069640
# ==========================================

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

active_tickets = {}

class TicketModal(discord.ui.Modal, title='📩 Создание тикета'):
    problem = discord.ui.TextInput(
        label='Имя, возраст, часы, пояс',
        style=discord.TextStyle.paragraph,
        placeholder='...',
        required=True,
        max_length=1000
    )
    user_id = discord.ui.TextInput(
        label='SteamID / Battlemetrics',
        placeholder='...',
        required=False,
        max_length=50
    )
    priority = discord.ui.TextInput(
        label='Опыт в кланах',
        placeholder='...',
        required=True,
        max_length=20
    )
    pc_specs = discord.ui.TextInput(
        label='ПК (CPU, GPU, RAM)',
        style=discord.TextStyle.short,
        placeholder='Например: i7-10700, RTX 3060, 16GB',
        required=True,
        max_length=200
    )
    battlemetrics_url = discord.ui.TextInput(
        label='Ссылка Battlemetrics',
        style=discord.TextStyle.short,
        placeholder='https://www.battlemetrics.com/...',
        required=True,
        max_length=200
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            if interaction.user.id in active_tickets:
                await interaction.response.send_message('❌ У вас уже есть открытый тикет!', ephemeral=True)
                return
            category = interaction.guild.get_channel(CATEGORY_ID)
            if not category:
                await interaction.response.send_message('❌ Категория не найдена.', ephemeral=True)
                return

            username = interaction.user.name.replace(' ', '-').lower()
            channel_name = f'ticket-{username}'

            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
                interaction.guild.get_role(SUPPORT_ROLE_ID): discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
                interaction.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
            }

            channel = await category.create_text_channel(channel_name, overwrites=overwrites)
            active_tickets[interaction.user.id] = channel.id

            embed = discord.Embed(title='✅ Тикет создан!', description='Спасибо за обращение.', color=discord.Color.green())
            embed.add_field(name='Имя, возраст, часы, пояс', value=self.problem.value, inline=False)
            if self.user_id.value:
                embed.add_field(name='SteamID / Battlemetrics', value=self.user_id.value, inline=True)
            embed.add_field(name='Опыт в кланах', value=self.priority.value, inline=True)
            embed.add_field(name='Характеристики ПК', value=self.pc_specs.value, inline=False)
            embed.add_field(name='Battlemetrics', value=self.battlemetrics_url.value, inline=False)
            embed.set_footer(text='Для закрытия нажмите кнопку ниже')

            close_view = CloseView()
            await channel.send(f'📌 {interaction.user.mention}', embed=embed, view=close_view)
            await interaction.response.send_message(f'✅ Тикет создан! Перейдите в {channel.mention}', ephemeral=True)
        except Exception as e:
            print(f"❌ Ошибка в модалке: {e}")
            await interaction.response.send_message(f'❌ Ошибка: {e}', ephemeral=True)

class CloseButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label='Закрыть тикет', style=discord.ButtonStyle.danger, custom_id='close_ticket')

    async def callback(self, interaction: discord.Interaction):
        await close_ticket_logic(interaction)

class CloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(CloseButton())

async def close_ticket_logic(interaction: discord.Interaction):
    try:
        if not isinstance(interaction.channel, discord.TextChannel) or interaction.channel.category_id != CATEGORY_ID:
            await interaction.response.send_message('❌ Этот канал не является тикетом.', ephemeral=True)
            return
        user = interaction.user
        support_role = interaction.guild.get_role(SUPPORT_ROLE_ID)
        is_owner = (user.id in active_tickets and active_tickets[user.id] == interaction.channel.id)
        is_support = support_role in user.roles
        if not (is_owner or is_support):
            await interaction.response.send_message('❌ У вас нет прав.', ephemeral=True)
            return
        if is_owner:
            del active_tickets[user.id]
        await interaction.response.send_message('⏳ Тикет будет закрыт через 5 секунд...')
        await asyncio.sleep(5)
        await interaction.channel.delete()
    except Exception as e:
        await interaction.response.send_message(f'❌ Ошибка: {e}', ephemeral=True)

class CreateTicketButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label='Создать тикет', style=discord.ButtonStyle.green, custom_id='create_ticket')

    async def callback(self, interaction: discord.Interaction):
        try:
            print("✅ Кнопка нажата, открываем модалку...")
            await interaction.response.send_modal(TicketModal())
            print("✅ Модалка успешно отправлена")
        except Exception as e:
            print(f"❌ Ошибка в кнопке: {e}")
            await interaction.response.send_message(f'❌ Не удалось открыть форму: {e}', ephemeral=True)

class TicketSetupView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(CreateTicketButton())

@bot.tree.command(name='setup', description='Отправить сообщение с кнопкой', guild=discord.Object(id=GUILD_ID))
async def setup(interaction: discord.Interaction):
    embed = discord.Embed(
        title='📩 Набор в клан RSG COMMUNITY',
        description='''
**ЧТО МЫ ПРЕДЛАГАЕМ**
• Реальный рост игроков
• Активность: участие в турнирах и игра на серверах x2
• Состав: дружный и адекватный состав без токсичности
• Лидер: опытный лидер с огромным стажем в клановой сфере Rust
• Работа над кланом 24/7

**ТРЕБОВАНИЯ К ТИКЕТАМ**
• Часы: 2500+
• Возраст: 16+ лет
• Онлайн: 8+ часов в сутки (активность строго контролируется)
• Дисциплина: уважение к тиммейтам и соблюдение правил
• Настрой: желание расти и работать в команде
• Присутствуют исключения для медиа-сферы и PvE*
• FFA Walls / FFA AK (35+ киллов за игру)
• FC R2 (45+ киллов за игру)

ㅤ
**Нажмите кнопку ниже, чтобы подать заявку в клан!**
        ''',
        color=discord.Color.blue()
    )
    embed.set_image(url="https://cdn.discordapp.com/attachments/1396600499234537533/1531396404772343998/Gemini_Generated_Image_zeqk2wzeqk2wzeqk.png")
    view = TicketSetupView()
    await interaction.response.send_message(embed=embed, view=view)

@bot.event
async def on_channel_delete(channel):
    for uid, cid in list(active_tickets.items()):
        if cid == channel.id:
            del active_tickets[uid]
            break

@bot.event
async def on_ready():
    await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
    print(f'✅ Бот {bot.user} запущен и готов к работе!')
    print(f'   Сервер: {bot.guilds[0].name if bot.guilds else "Не найден"}')
    print('   Используйте /setup в нужном канале, чтобы создать кнопку.')

# ===== ВЕБ-СЕРВЕР ДЛЯ RENDER (НАСТОЯЩИЙ, РАБОЧИЙ) =====
app = Flask(__name__)

@app.route('/')
def hello():
    return "Бот работает!", 200

@app.route('/health')
def health():
    return "OK", 200

def run_web():
    # Запускаем Flask на порту 8080
    app.run(host='0.0.0.0', port=8080, debug=False, threaded=True)

# ===== ЗАПУСК =====
if __name__ == '__main__':
    # Запускаем Flask в отдельном потоке
    web_thread = threading.Thread(target=run_web, daemon=True)
    web_thread.start()
    print("🌐 Веб-сервер запущен на порту 8080")
    # Запускаем бота
    bot.run(TOKEN)
