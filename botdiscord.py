import discord
from discord.ext import commands
import re
import asyncio
from datetime import datetime, timedelta
import math

from discord.ui import View, Select, Button, Modal, TextInput

# إعداد Intent للمحتوى الرسالة والأعضاء
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# تعريف البوت (تم تعديل هذا السطر ليشمل '$' كـ prefix)
bot = commands.Bot(command_prefix=['!', '$'], intents=intents)

# قاعدة بيانات النقاط (في الواقع يجب استخدام قاعدة بيانات حقيقية)
points_db = {}
line_channel = None
auto_clear_rooms = {}

# شراء رتب
PROBOT_ID = 282859044593598464
YOUR_BOT_RECEIVING_ID = 1111009049773871115
# معرف المالك الذي يمكنه استخدام أمر !apply
OWNER_ID_FOR_APPLY = 1111009049773871115
# معرف القناة التي ستصل إليها التقديمات بعد ملء النموذج
APPLICATIONS_CHANNEL_ID = 1329193614420606986
PRICES_CHANNEL_ID = 123456789012345678 # ضع معرف قناة الأسعار الصحيح هنا

# قاموس معلومات الرتب: الاسم -> {ID, السعر}
ROLE_PURCHASE_INFO = {
    'Traderl S': {'id': 1331353818063175711, 'price': 1500000},
    'Vendor S': {'id': 1331353819078066316, 'price': 1000000},
    'Merchant S': {'id': 1331353820089024522, 'price': 700000},
    'Marketer S': {'id': 1331356926155427920, 'price': 500000},
    'Developer S': {'id': 1331353825700876402, 'price': 250001},
    'Designe S': {'id': 1331356913367126246, 'price': 250000}
}

# قائمة لعرضها في القائمة المنسدلة
PURCHASABLE_ROLES_OPTIONS = [
    discord.SelectOption(label=name, value=name, description=f"السعر: {info['price']}$")
    for name, info in ROLE_PURCHASE_INFO.items()
]

# دالة مساعدة لحساب الضريبة (تم التعديل)
def calculate_tax(amount):
    # حساب المبلغ الذي يجب تحويله لكي يصل المبلغ الصافي المطلوب بعد خصم 5% ضريبة
    return math.ceil(amount / 0.95)

# --- متغيرات نظام عملة RC الجديدة ---
RC_LOGS_CHANNEL_ID = 1391919182358122507 # معرف قناة سجلات تحويلات RC (تم تحديث هذا المعرف)
RC_EMOJI = "<:RC:1391916710461837504>" # الايموجي الخاص بعملة RC (يرجى تعديل هذا)
OWNER_USER_ID = 1111009049773871115 # هذا هو معرفك الخاص كمالك البوت (تم استخدام YOUR_BOT_RECEIVING_ID)

rc_balances = {} # قاموس لتخزين رصيد العملة RC لكل عضو {user_id: amount}
# ملاحظة: هذا التخزين مؤقت. سيتم مسح الأرصدة عند إغلاق البوت. للحفظ الدائم، تحتاج إلى استخدام ملف (مثل JSON) أو قاعدة بيانات.
# --------------------------------------------------

# -------------------------------------------------------------
# متغيرات وإعدادات نظام التذاكر الجديدة
# -------------------------------------------------------------

# ID الكاتيجوري الذي ستُنشأ فيه التذاكر
TICKET_CATEGORY_ID = 1351648865555582986
# ID الرتبة التي يمكنها رؤية التذاكر والرد عليها
STAFF_ROLE_ID = 1331333647596388402
# ID القناة التي سترسل إليها معلومات الشراء (من زر الشراء في التذكرة)
PRICES_CHANNEL_ID = 1328069140853821550
# ID القناة التي سترسل إليها رسائل مكافأة الاستلام
RECEIVE_LOG_CHANNEL_ID = 1391865645154697256
# ID قناة سجلات التذاكر
TICKET_LOG_CHANNEL_ID = 1329192951275978812

# قاعدة بيانات مؤقتة للتذاكر المفتوحة (للتتبع)
# ستكون كالتالي: { user_id: channel_id }
open_tickets = {}

# -------------------------------------------------------------
# نهاية متغيرات وإعدادات نظام التذاكر
# -------------------------------------------------------------

# دالة لتوليد مفتاح تحويلة عشوائي الشكل
def generate_transfer_key():
    characters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    key_parts = []
    # Use current datetime parts to get some "randomness"
    now = datetime.now()
    seed_base = now.microsecond + now.second + now.minute + now.hour + now.day + now.month + now.year

    for i in range(3):
        part = ""
        for j in range(4):
            # Simple pseudo-random index generation
            index = (seed_base + i * 100 + j * 10) % len(characters)
            part += characters[index]
            seed_base = (seed_base * 7 + 13) % 999999 # Simple scrambling for next character
        key_parts.append(part)
    return " ".join(key_parts)


@bot.event
async def on_ready():
    print(f'تم تسجيل الدخول كـ {bot.user.name} ({bot.user.id})')
    print('البوت جاهز للعمل! - نظام بيع الرتب جاهز.')
    print('----------------------------------------------------')
    print(f'معرف ProBot: {PROBOT_ID}')
    print(f'معرف البوت المستلم: {YOUR_BOT_RECEIVING_ID}')
    print('----------------------------------------------------')
    print(f'معرف كاتيجوري التذاكر: {TICKET_CATEGORY_ID}')
    print(f'معرف رتبة الطاقم: {STAFF_ROLE_ID}')
    print(f'معرف قناة الأسعار: {PRICES_CHANNEL_ID}')
    print(f'معرف قناة سجلات الاستلام: {RECEIVE_LOG_CHANNEL_ID}')
    print(f'معرف قناة سجلات التذاكر: {TICKET_LOG_CHANNEL_ID}')
    print(f'معرف قناة سجلات تحويلات RC: {RC_LOGS_CHANNEL_ID}')
    print('----------------------------------------------------')

    for channel_id in list(auto_clear_rooms.keys()):
        try:
            channel = await bot.fetch_channel(channel_id)
            auto_clear_rooms[channel_id]['task'] = bot.loop.create_task(clear_channel_every_24h(channel))
        except:
            print(f"لم يتمكن البوت من إعادة تشغيل مهمة d24h للروم {channel_id}.")
            if channel_id in auto_clear_rooms:
                del auto_clear_rooms[channel_id]

# --- نظام عملة RC الجديد (أضف هذا الكود كاملاً) ---

@bot.command(name='RC', aliases=['rc'])
async def rc_balance_or_transfer(ctx, target: discord.Member = None, amount: int = None):
    # إذا لم يتم تقديم أي وسائط، اعرض رصيد المرسل
    if target is None and amount is None:
        balance = rc_balances.get(ctx.author.id, 0)
        await ctx.send(f"** يملك {ctx.author.mention} {balance} {RC_EMOJI} **")
        print(f"[RC] User {ctx.author.name} checked their balance: {balance} RC.")
        return

    # إذا تم تقديم الهدف ولكن ليس المبلغ، افترض أنهم يريدون التحقق من رصيد الهدف
    if target and amount is None:
        balance = rc_balances.get(target.id, 0)
        await ctx.send(f"** يملك {target.mention} {balance} {RC_EMOJI} **")
        print(f"[RC] User {ctx.author.name} checked {target.name}'s balance: {balance} RC.")
        return

    # منطق التحويل
    if target and amount is not None:
        if amount <= 0:
            await ctx.send("❌ المبلغ يجب أن يكون رقماً موجباً.", ephemeral=True)
            return

        sender_balance = rc_balances.get(ctx.author.id, 0)
        if sender_balance < amount:
            await ctx.send(f"❌ ليس لديك رصيد كافٍ لتحويل {amount} {RC_EMOJI}. رصيدك الحالي: {sender_balance} {RC_EMOJI}.", ephemeral=True)
            return

        # تنفيذ التحويل
        rc_balances[ctx.author.id] = sender_balance - amount
        rc_balances[target.id] = rc_balances.get(target.id, 0) + amount

        # توليد مفتاح التحويلة
        transfer_key = generate_transfer_key()

        await ctx.send(f"** تم تحويل {amount} {RC_EMOJI} الى {target.mention} من قبل {ctx.author.mention}**")
        print(f"[RC] {ctx.author.name} transferred {amount} RC to {target.name}.")

        # إرسال رسالة خاصة للمستقبل
        try:
            await target.send(
                f"** تم تحويل لك {amount} {RC_EMOJI}\n"
                f"المحول ``` {ctx.author.id} {ctx.author.name} ```\n"
                f"المستلم ``` {target.id} {target.name} ```\n"
                f"مفتاح التحويلة {transfer_key} **"
            )
            print(f"[RC PM] Sent private message to {target.name} about receiving RC.")
        except discord.Forbidden:
            print(f"[RC PM] Could not send private message to {target.name}. User has DMs disabled or bot is blocked.")

        # تسجيل المعاملة في قناة السجلات (تم تعديل المحتوى ليشمل المفتاح)
        log_channel = bot.get_channel(RC_LOGS_CHANNEL_ID)
        if log_channel:
            embed_log = discord.Embed(
                title="تحويل RC",
                description=(
                    f"**المرسل:** {ctx.author.mention} (ID: {ctx.author.id})\n"
                    f"**المستقبل:** {target.mention} (ID: {target.id})\n"
                    f"**المبلغ:** {amount} {RC_EMOJI}\n"
                    f"**رصيد المرسل الجديد:** {rc_balances[ctx.author.id]} {RC_EMOJI}\n"
                    f"**رصيد المستقبل الجديد:** {rc_balances[target.id]} {RC_EMOJI}\n"
                    f"**مفتاح التحويلة:** `{transfer_key}`" # إضافة المفتاح هنا
                ),
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            await log_channel.send(embed=embed_log)
            await log_channel.send(f"```{transfer_key}```") # إرسال المفتاح بشكل منفصل كما طلب المستخدم
            print(f"[RC Log] Sent transfer log to channel {RC_LOGS_CHANNEL_ID}.")
        else:
            print(f"[RC Log] Could not find log channel with ID: {RC_LOGS_CHANNEL_ID}.")

@bot.command(name='GIVERC', aliases=['giverc'])
async def give_rc(ctx, target: discord.Member, amount: int):
    # التحقق من أن المستخدم هو المالك
    if ctx.author.id != OWNER_USER_ID:
        await ctx.send("❌ ليس لديك الصلاحية لاستخدام هذا الأمر.", ephemeral=True)
        print(f"[RC Admin] {ctx.author.name} tried to use GIVERC without permission.")
        return

    if amount <= 0:
        await ctx.send("❌ المبلغ يجب أن يكون رقماً موجباً.", ephemeral=True)
        return

    rc_balances[target.id] = rc_balances.get(target.id, 0) + amount
    await ctx.send(f"** تم إضافة {amount} {RC_EMOJI} الى {target.mention} من قبل {ctx.author.mention}**")
    print(f"[RC Admin] {ctx.author.name} added {amount} RC to {target.name}. New balance: {rc_balances[target.id]}.")

    # تسجيل المعاملة في قناة السجلات (تم تعديل المحتوى ليشمل المفتاح)
    log_channel = bot.get_channel(RC_LOGS_CHANNEL_ID)
    if log_channel:
        transfer_key = generate_transfer_key() # توليد مفتاح هنا أيضاً
        embed_log = discord.Embed(
            title="إضافة RC بواسطة المالك",
            description=(
                f"**المضاف إليه:** {target.mention} (ID: {target.id})\n"
                f"**المبلغ المضاف:** {amount} {RC_EMOJI}\n"
                f"**بواسطة:** {ctx.author.mention} (ID: {ctx.author.id})\n"
                f"**رصيد {target.name} الجديد:** {rc_balances[target.id]} {RC_EMOJI}\n"
                f"**مفتاح التحويلة:** `{transfer_key}`" # إضافة المفتاح هنا
            ),
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        await log_channel.send(embed=embed_log)
        await log_channel.send(f"```{transfer_key}```") # إرسال المفتاح بشكل منفصل كما طلب المستخدم
        print(f"[RC Log] Sent admin give log to channel {RC_LOGS_CHANNEL_ID}.")
    else:
        print(f"[RC Log] Could not find log channel with ID: {RC_LOGS_CHANNEL_ID}.")

# اختياري: أمر لمسح سجلات الرصيد (للمالك فقط)
@bot.command(name='CLEARRC', aliases=['clearrc'])
async def clear_rc(ctx, target: discord.Member = None):
    if ctx.author.id != OWNER_USER_ID:
        await ctx.send("❌ ليس لديك الصلاحية لاستخدام هذا الأمر.", ephemeral=True)
        return
    
    if target:
        if target.id in rc_balances:
            del rc_balances[target.id]
            await ctx.send(f"✅ تم مسح رصيد {target.mention} من عملة RC.", ephemeral=True)
            print(f"[RC Admin] Cleared RC balance for {target.name}.")
        else:
            await ctx.send(f"❌ {target.mention} لا يملك رصيد RC.", ephemeral=True)
            print(f"[RC Admin] Tried to clear RC for {target.name} but no balance found.")
    else:
        # مسح جميع الأرصدة (يتطلب تأكيداً)
        await ctx.send("❓ هل أنت متأكد أنك تريد مسح جميع أرصدة RC؟ أرسل `نعم` للتأكيد.")
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() == 'نعم'
        
        try:
            msg = await bot.wait_for('message', check=check, timeout=30.0)
            rc_balances.clear()
            await ctx.send("✅ تم مسح جميع أرصدة RC بنجاح.")
            print("[RC Admin] All RC balances cleared.")
        except asyncio.TimeoutError:
            await ctx.send("❌ تم إلغاء عملية مسح جميع أرصدة RC.", ephemeral=True)
            print("[RC Admin] All RC balances clear operation cancelled.")

# معالجة الأخطاء للأوامر
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ خطأ: لم تقدم جميع المتطلبات. الاستخدام الصحيح: `{ctx.prefix}{ctx.command.name} {ctx.command.signature}`", ephemeral=True)
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"❌ خطأ: نوع خاطئ للمدخلات. يرجى التأكد من منشن العضو والمبلغ رقم.", ephemeral=True)
    elif isinstance(error, commands.CheckFailure): # لأوامر مثل has_role أو is_owner
        await ctx.send("❌ ليس لديك الصلاحية لاستخدام هذا الأمر.", ephemeral=True)
    elif isinstance(error, commands.CommandNotFound):
        # يمكنك ترك هذا فارغا إذا كنت لا تريد أن يرد البوت على الأوامر غير الموجودة
        # print(f"Command '{ctx.message.content}' not found.")
        pass
    else:
        print(f"**[خطأ في الأمر]** حدث خطأ غير متوقع في الأمر '{ctx.command.name}': {error}")
        await ctx.send(f"❌ حدث خطأ غير متوقع أثناء تنفيذ الأمر: {error}", ephemeral=True)

# --------------------------------------------------

@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user:
        return

    # 1. معالجة رسائل ProBot (لتحويلات الرتب)
    if message.author.id == PROBOT_ID:
        print(f"\n**[تتبع]** رسالة جديدة من ProBot في القناة: {message.channel.name} ({message.channel.id})")
        print(f"**[تتبع]** محتوى الرسالة: {message.content}")

        match = re.search(
            r':moneybag:\s*\|\s*(.+?),\s*has transferred\s*`\$(\d+)\s*`\s*to\s*<@!?' + re.escape(str(YOUR_BOT_RECEIVING_ID)) + r'>',
            message.content
        )

        if match:
            user_display_name_raw = match.group(1).strip()
            amount_transferred = int(match.group(2))

            print(f"**[تتبع ProBot]** رسالة ProBot تم تحليلها بنجاح!")
            print(f"**[تتبع ProBot]** المستخدم المُحول (الاسم الخام): '{user_display_name_raw}'")
            print(f"**[تتبع ProBot]** المبلغ المُحول (صافي): {amount_transferred}")

            member_found = None
            if message.guild:
                user_id_from_mention_match = re.search(r'<@!?(\d+)>', user_display_name_raw)
                if user_id_from_mention_match:
                    try:
                        user_id_from_mention = int(user_id_from_mention_match.group(1))
                        member_found = message.guild.get_member(user_id_from_mention)
                        if member_found:
                            print(f"**[تتبع ProBot]** تم العثور على العضو بواسطة ID من المنشنة: {member_found.display_name} ({member_found.id})")
                    except ValueError:
                        pass

                if not member_found:
                    clean_name = re.sub(r'#M|@!#\s*', '', user_display_name_raw).strip()

                    for member in message.guild.members:
                        if member.display_name.lower() == clean_name.lower():
                            member_found = member
                            print(f"**[تتبع ProBot]** تم العثور على العضو بواسطة الاسم الظاهر: {member_found.display_name} ({member.id})")
                            break
                    if not member_found:
                        for member in message.guild.members:
                            if member.name.lower() == clean_name.lower():
                                member_found = member
                                print(f"**[تتبع ProBot]** تم العثور على العضو بواسطة الاسم العادي: {member.name} ({member.id})")
                                break

            if member_found:
                print(f"**[تتبع ProBot]** تم العثور على العضو في السيرفر: {member_found.display_name} ({member_found.id})")

                found_role_to_give = None
                for role_name, info in ROLE_PURCHASE_INFO.items():
                    if amount_transferred == info['price']:
                        found_role_to_give = message.guild.get_role(info['id'])
                        if found_role_to_give:
                            break

                if found_role_to_give:
                    try:
                        if found_role_to_give in member_found.roles:
                            await message.channel.send(
                                f"أهلًا بك {member_found.mention}، لقد قمت بتحويل `{amount_transferred}$` كريدت."
                                f" أنت تمتلك بالفعل رتبة `{found_role_to_give.name}`."
                            )
                            print(f"**[تتبع ProBot]** العضو {member_found.display_name} يمتلك بالفعل الرتبة: {found_role_to_give.name}.")
                        else:
                            await member_found.add_roles(found_role_to_give)
                            await message.channel.send(
                                f"تهانينا {member_found.mention}!\nلقد قمت بتحويل `{amount_transferred}$` كريدت."
                                f" وتم منحك رتبة **{found_role_to_give.name}** بنجاح!"
                            )
                            print(f"**[تتبع ProBot]** تم منح الرتبة **{found_role_to_give.name}** للعضو {member_found.display_name}.")
                    except discord.Forbidden:
                        await message.channel.send(
                            f"أهلًا بك {member_found.mention}، لقد قمت بتحويل `{amount_transferred}$` كريدت."
                            f" لكن لا أمتلك صلاحية منح الرتب. يرجى مراجعة صلاحياتي (Manage Roles)."
                        )
                        print(f"**[خطأ صلاحيات ProBot]** البوت لا يملك صلاحية 'إدارة الرتب' في السيرفر. تأكد أن رتبته أعلى من رتبة الهدف.")
                    except Exception as e:
                        await message.channel.send(
                            f"أهلًا بك {member_found.mention}، لقد قمت بتحويل `{amount_transferred}$` كريدت."
                            f" حدث خطأ غير متوقع عند محاولة منحك الرتبة. يرجى التواصل مع الإدارة."
                        )
                        print(f"**[خطأ عام ProBot]** حدث خطأ غير متوقع عند منح الرتبة للعضو {member_found.display_name}: {e}")
                # تم إزالة جزء الـ "else" هنا لتجاهل التحويلات غير المطابقة للرتب

            else:
                print(f"**[تحذير ProBot]** لم يتم العثور على العضو '{user_display_name_raw}' في السيرفر.")
        else:
            print(f"**[تتبع ProBot]** رسالة ProBot من {message.author.name} لم تطابق نمط التحويل المتوقع: {message.content}")

        return

    # 2. معالجة الرسائل في روم الخط المفعّل
    if line_channel and message.channel.id == line_channel.id:
        if not message.content.strip().startswith('!') and message.author.id != PROBOT_ID and message.content.strip():
            try:
                await message.channel.send("https://i.postimg.cc/sXqfZkwt/Revolver-s-3.png")
                print(f"**تتبع (خط تلقائي):** تم إرسال خط تلقائي في {message.channel.name} بعد رسالة من {message.author.name}.")
            except discord.Forbidden:
                print(f"**خطأ (صلاحيات):** البوت لا يملك صلاحية إرسال الرسائل في قناة الخط التلقائي ({message.channel.name}).")
            except Exception as e:
                print(f"**خطأ (خط تلقائي):** حدث خطأ غير متوقع عند إرسال الخط التلقائي: {e}")

    # 3. معالجة الأوامر الأخرى
    await bot.process_commands(message)


# أمر "خط"
@bot.command(name='خط')
@commands.has_any_role(1331333646723977249, 1331332308745064499)
async def line_command(ctx: commands.Context):
    """يرسل صورة خط ويمسح الأمر."""
    try:
        await ctx.message.delete()
        await ctx.send("https://i.postimg.cc/sXqfZkwt/Revolver-s-3.png")
        print(f"**تتبع (خط):** تم تنفيذ أمر !خط بواسطة {ctx.author.name} في {ctx.channel.name}")
    except discord.Forbidden:
        print(f"**خطأ (صلاحيات):** البوت لا يملك صلاحية حذف الرسائل أو إرسال الرسائل في القناة {ctx.channel.name} عند تنفيذ أمر !خط.")
        await ctx.send("❌ لا أمتلك الصلاحيات اللازمة لحذف رسالتك أو إرسال الخط هنا. يرجى مراجعة صلاحياتي.", delete_after=5)
    except Exception as e:
        print(f"**خطأ (خط):** حدث خطأ غير متوقع عند تنفيذ أمر !خط: {e}")
        await ctx.send("❌ حدث خطأ غير متوقع عند محاولة إرسال الخط.", delete_after=5)


@bot.command()
@commands.has_role(1331333646723977249)
async def come(ctx, user: discord.Member):
    """يرسل نداء خاص لعضو"""
    try:
        await user.send(f'** تم نداء {user.mention} الى روم {ctx.channel.mention} من طرف {ctx.author.mention} <:R25:1384226496583041024> **')
        await ctx.send(f'تم إرسال النداء إلى {user.mention} بنجاح!')
    except:
        await ctx.send('لا يمكن إرسال رسالة خاصة لهذا المستخدم!')

@bot.command()
@commands.has_role(1331332308745064499)
async def say(ctx, *, text):
    """يقول البوت ما يكتبه المستخدم"""
    await ctx.send(text)
    await ctx.message.delete()

@bot.command()
async def tax(ctx, amount: str):
    """حساب الضريبة"""
    amount_lower = amount.lower()
    multiplier = 1
    if 'm' in amount_lower:
        multiplier = 1000000
        amount = amount_lower.replace('m', '')
    elif 'k' in amount_lower:
        multiplier = 1000
        amount = amount_lower.replace('k', '')

    try:
        original_amount = float(amount) * multiplier
        taxed_amount = calculate_tax(original_amount)
        await ctx.send(f'** ضريبة {int(original_amount)} هي {int(taxed_amount)}{RC_EMOJI} **') # تم تعديل هنا لعرض عدد صحيح
    except ValueError:
        await ctx.send('المبلغ غير صالح!')

@bot.command()
@commands.has_role(1331333646723977249)
async def points(ctx, user: discord.Member = None):
    """عرض نقاط العضو"""
    target = user or ctx.author
    points = points_db.get(target.id, 0)
    await ctx.send(f'** يملك {target.mention} {points} 🪙 **')

@bot.command()
@commands.has_role(1331333453584662589)
async def addpoints(ctx, user: discord.Member, points: int):
    """إضافة نقاط لعضو"""
    points_db[user.id] = points_db.get(user.id, 0) + points
    await ctx.send(f'تم إضافة {points} نقطة لـ {user.mention}')

@bot.command()
@commands.has_role(1331333646723977249)
async def topstaff(ctx):
    """عرض أعلى الأعضاء بالنقاط"""
    sorted_users = sorted(points_db.items(), key=lambda x: x[1], reverse=True)[:10]
    embed = discord.Embed(title="أعضاء الإدارة حسب النقاط", color=0x00ff00)

    for user_id, points in sorted_users:
        user = await bot.fetch_user(user_id)
        embed.add_field(name=user.name, value=f"{points} نقطة", inline=False)

    await ctx.send(embed=embed)

@bot.command()
@commands.has_role(1331332308745064499)
async def rstpoints(ctx):
    """إعادة تعيين جميع النقاط"""
    points_db.clear()
    await ctx.send('تم إعادة تعيين جميع النقاط إلى الصفر')

@bot.command()
@commands.has_role(1331332308745064499)
async def tlabat(ctx):
    """إنشاء رسالة الطلبات مع صورة كبيرة"""
    try:
        embed = discord.Embed(
            title="Revolver | الطلبات",
            description="** __ الطلبات <:R6:1384225879357522081> ___ \n\n"
                        "اطلب طلبك بإحترام <:R22:1384226486541881466>\n"
                        "إلتزام بقوانين <:R22:1384226486541881466>\n"
                        "التشفـير <:R22:1384226486541881466>\n"
                        "عدم الإستهبال في الطلب <:R22:1384226486541881466>**",
            color=0x23c536
        )
        embed.set_image(url="https://i.postimg.cc/SsHmZHyp/8.png") # تم تحديث الصورة هنا

        button = discord.ui.Button(
            style=discord.ButtonStyle.gray,
            label="الغرض",
            emoji="<:R15:1384226111428366386>"
        )

        async def button_callback(interaction):
            modal = discord.ui.Modal(title="إرسال طلب")
            purpose = discord.ui.TextInput(
                label="ما هو غرض طلبك؟",
                style=discord.TextStyle.long,
                placeholder="اكتب طلبك هنا...",
                required=True
            )
            modal.add_item(purpose)

            async def modal_callback(interaction):
                channel = bot.get_channel(1328634315101175869)
                if channel:
                    request_embed = discord.Embed(
                        title="طلب جديد",
                        description=f"**الطلب من {interaction.user.mention}:**\n\n{purpose.value}",
                        color=0x23c536
                    )
                    await channel.send(embed=request_embed)
                    await interaction.response.send_message("تم إرسال طلبك بنجاح!", ephemeral=True)

            modal.on_submit = modal_callback
            await interaction.response.send_modal(modal)

        button.callback = button_callback

        view = discord.ui.View()
        view.add_item(button)

        await ctx.send(embed=embed, view=view)

    except Exception as e:
        await ctx.send(f"حدث خطأ: {str(e)}")


@bot.command()
@commands.has_role(1331332308745064499)
async def line_on(ctx, channel_id: int):
    """تفعيل إرسال الخط التلقائي في روم عند أي رسالة."""
    global line_channel
    try:
        channel = await bot.fetch_channel(channel_id)
        line_channel = channel
        await ctx.send(f"✅ تم تفعيل إرسال الخط التلقائي في {channel.mention}")
        print(f"**تتبع (line_on):** تم تفعيل الخط التلقائي في القناة ID: {channel_id}")
    except discord.NotFound:
        await ctx.send("❌ لم أستطع العثور على القناة بهذا المعرف. تأكد من صحة الـ ID.", delete_after=5)
        print(f"**خطأ (line_on):** لم يتم العثور على القناة بمعرف {channel_id}.")
    except discord.Forbidden:
        await ctx.send("❌ ليس لدي صلاحية الوصول لهذه القناة. تأكد من صلاحياتي.", delete_after=5)
        print(f"**خطأ (line_on):** البوت لا يملك صلاحية الوصول للقناة بمعرف {channel_id}.")
    except Exception as e:
        await ctx.send(f"❌ حدث خطأ غير متوقع: {str(e)}", delete_after=5)
        print(f"**خطأ (line_on):** حدث خطأ غير متوقع: {e}")

@bot.command()
@commands.has_role(1331332308745064499)
async def line_off(ctx):
    """إيقاف إرسال الخط التلقائي."""
    global line_channel
    if line_channel:
        await ctx.send(f"❌ تم إيقاف إرسال الخط في {line_channel.mention}")
        print(f"**تتبع (line_off):** تم إيقاف الخط التلقائي في القناة ID: {line_channel.id}")
        line_channel = None
    else:
        await ctx.send("⚠️ لا يوجد روم مفعل لإرسال الخط")
        print("**تتبع (line_off):** لا يوجد روم مفعل لإيقاف الخط التلقائي.")


@bot.command()
@commands.has_role(1331332308745064499)
async def send(ctx, message_id: int = None, *, custom_text: str = None):
    """إرسال رسالة مخصصة مع صورة ولون أخضر"""
    try:
        image_url = None
        if ctx.message.attachments:
            image_url = ctx.message.attachments[0].url

        embed = discord.Embed(color=0x23c536)

        if image_url:
            embed.set_image(url=image_url)

        if message_id:
            original_msg = await ctx.channel.fetch_message(message_id)
            if original_msg.content:
                embed.description = original_msg.content
            if not image_url and original_msg.attachments:
                embed.set_image(url=original_msg.attachments[0].url)

        if custom_text:
            embed.add_field(name="الرسالة", value=custom_text, inline=False)

        await ctx.send(embed=embed)
        await ctx.message.delete()

    except Exception as e:
        await ctx.send(f"❌ خطأ: {str(e)}")

@bot.command()
@commands.has_role(1331332308745064499)
async def tchfir(ctx):
    """إنشاء واجهة تشفير النصوص مع الصورة"""
    embed = discord.Embed(
        title="Revolver | التشفير",
        description="**اضغط الزر لكي تشفر النص الخاص بك <:R5:1384225871317176331>**",
        color=0x23c536
    )
    embed.set_image(url="https://i.postimg.cc/wvRpsFD4/s.png") # تم تحديث الصورة هنا

    button = discord.ui.Button(
        style=discord.ButtonStyle.gray,
        label="التشفير",
        emoji="<:R5:1384225871317176331>"
    )

    async def button_callback(interaction):
        modal = discord.ui.Modal(title="تشفير النص")
        text_input = discord.ui.TextInput(
            label="أدخل النص الذي تريد تشفيره",
            style=discord.TextStyle.long,
            placeholder="اكتب النص هنا...",
            required=True
        )
        modal.add_item(text_input)

        async def modal_callback(interaction):
            cipher_dict = {
                'حسابات': '7سابات', 'حساب': '7ساب', 'ديسكورد': 'ديسك9رد', 'بيع': 'بي3',
                'بائع': 'بائ3', 'شراء': 'شر1ء', 'نيترو': 'نيتر9', 'نيتروهات': 'نيتر9هات',
                'متوفر': 'مت9فر', 'السعر': 'الس3ر', 'سعر': 'س3ر', 'اشتري': '1شتري'
            }
            text = text_input.value
            for word, encrypted in cipher_dict.items():
                text = text.replace(word, encrypted)

            copy_button = discord.ui.Button(
                style=discord.ButtonStyle.green,
                label="نسخ النص",
                emoji="📋"
            )

            async def copy_button_callback(interaction):
                await interaction.user.send(f"**النص المشفر:**\n{text}")
                await interaction.followup.send("تم إرسال النص إلى خاصك!", ephemeral=True)

            copy_button.callback = copy_button_callback

            view = discord.ui.View()
            view.add_item(copy_button)

            await interaction.response.send_message(
                f"**تم تشفير النص بنجاح!**\nاستخدم الزر لنسخه:\n\n{text}",
                view=view,
                ephemeral=True
            )

        modal.on_submit = modal_callback
        await interaction.response.send_modal(modal)

    button.callback = button_callback

    view = discord.ui.View()
    view.add_item(button)

    await ctx.send(embed=embed, view=view)

# حذف 24سا

@bot.command()
@commands.has_role(1331332308745064499)
async def d24h(ctx, channel_id: int):
    """تفعيل/تعطيل الحذف التلقائي كل 24 ساعة للروم"""
    try:
        channel = await bot.fetch_channel(channel_id)

        if channel_id in auto_clear_rooms:
            auto_clear_rooms[channel_id]['task'].cancel()
            del auto_clear_rooms[channel_id]
            await ctx.send(f"✅ تم تعطيل الحذف التلقائي في {channel.mention}")
        else:
            task = bot.loop.create_task(clear_channel_every_24h(channel))
            auto_clear_rooms[channel_id] = {
                'channel': channel,
                'task': task,
                'last_cleared': datetime.now()
            }
            await ctx.send(f"✅ تم تفعيل الحذف التلقائي كل 24 ساعة في {channel.mention}")
    except Exception as e:
        await ctx.send(f"❌ خطأ: تأكد من صحة أي دي الروم وأن البوت لديه الصلاحيات اللازمة. الخطأ: {str(e)}")

async def clear_channel_every_24h(channel):
    while True:
        try:
            await asyncio.sleep(86400) # 24 hours

            deleted_messages = await channel.purge(limit=None)
            print(f"تم حذف {len(deleted_messages)} رسالة من الروم {channel.name} في {datetime.now()}")

        except Exception as e:
            print(f"حدث خطأ في مهمة الحذف التلقائي لروم {channel.name}: {str(e)}")
            await asyncio.sleep(3600) # Wait an hour before retrying
            continue

# أمر !اشتري الجديد
@bot.command(name='اشتري')
async def buy_role(ctx):
    """ يعرض خيارات شراء الرتب بقائمة منسدلة. """
    prices_channel_id = 1328069140853821550
    embed = discord.Embed(
        title="شراء الرتب",
        description=f"** لروئية اسعار و معلومات الرتب توجه الى <#{prices_channel_id}> <:R12:1384226030788546660> **\n\n"
                    "**اختر الرتبة التي ترغب بشرائها من القائمة أدناه:**",
        color=0x23c536
    )
    class RoleSelect(Select):
        def __init__(self):
            super().__init__(
                placeholder="اختر رتبة...",
                min_values=1,
                max_values=1,
                options=PURCHASABLE_ROLES_OPTIONS
            )
        async def callback(self, interaction: discord.Interaction):
            selected_role_name = self.values[0]
            role_info = ROLE_PURCHASE_INFO.get(selected_role_name)
            if role_info:
                original_price = role_info['price']
                price_with_tax = calculate_tax(original_price)
                # الرسالة المعدلة: فقط الأمر القابل للنسخ
                await interaction.response.send_message(
                    f"**انسخ الأمر التالي وحوله في ProBot:**\n"
                    f"```c {YOUR_BOT_RECEIVING_ID} {int(price_with_tax)}```\n"
                    f"**لقد اخترت رتبة {selected_role_name}.**\n"
                    f"المبلغ الصافي الذي سيصل إلي هو `{original_price}$`.", ephemeral=True
                )
            else:
                await interaction.response.send_message("حدث خطأ في تحديد الرتبة. يرجى المحاولة مرة أخرى.", ephemeral=True)
    view = View()
    view.add_item(RoleSelect())
    await ctx.send(embed=embed, view=view)

# -------------------------------------------------------------
# أمر !apply الجديد (نظام التقديمات المحدد بطلبك)
# -------------------------------------------------------------
class CustomApplyModal(Modal, title="نموذج التقديم للإدارة"):
    # تم تغيير label و placeholder هنا
    name_age_country = TextInput(
        label="الاسم، العمر، البلد",
        placeholder="مثال: محمد، 20 سنة، الجزائر",
        required=True,
        max_length=100
    )
    interaction_duration = TextInput(
        label="مدة تفاعلك في السيرفر",
        placeholder="مثال: 3 ساعات يومياً / متفاعل معظم الوقت",
        required=True,
        max_length=100
    )
    reason_for_applying = TextInput(
        label="سبب التقديم",
        placeholder="لماذا ترغب في الانضمام إلى الإدارة؟",
        required=True,
        style=discord.TextStyle.paragraph
    )
    experiences = TextInput(
        label="خبراتك السابقة",
        placeholder="اذكر أي خبرات لديك في الإدارة أو المجال",
        required=False,
        style=discord.TextStyle.paragraph
    )
    rv_logo = TextInput(
        label="هل وضعت شعار (RV) في اسمك؟\n(نعم/لا)",
        placeholder="أجب بنعم أو لا",
        required=True,
        max_length=5
    )
    async def on_submit(self, interaction: discord.Interaction):
        applications_channel = bot.get_channel(APPLICATIONS_CHANNEL_ID)
        if not applications_channel:
            print(f"**[خطأ في التقديم]** لم يتم العثور على قناة التقديمات بالـ ID: {APPLICATIONS_CHANNEL_ID}")
            await interaction.response.send_message("حدث خطأ في إرسال طلبك. قناة التقديمات غير موجودة. يرجى إبلاغ الإدارة.", ephemeral=True)
            return
        embed = discord.Embed(
            title="تقديم جديد للإدارة!",
            color=0x7289DA, # لون Discord الأزرق
            timestamp=datetime.now()
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.add_field(name="المرسل", value=f"{interaction.user.mention} (`{interaction.user.id}`)", inline=False)
        embed.add_field(name="الاسم، العمر، البلد", value=self.name_age_country.value, inline=False)
        embed.add_field(name="مدة التفاعل", value=self.interaction_duration.value, inline=False)
        embed.add_field(name="سبب التقديم", value=self.reason_for_applying.value, inline=False)
        embed.add_field(name="الخبرات السابقة", value=self.experiences.value if self.experiences.value else "لا يوجد", inline=False)
        embed.add_field(name="وضع شعار (RV)", value=self.rv_logo.value, inline=False)
        try:
            await applications_channel.send(f"تقديم جديد من {interaction.user.mention}:", embed=embed)
            await interaction.response.send_message("✅ تم إرسال طلب تقديمك للإدارة بنجاح!\nسيتم مراجعته قريباً.", ephemeral=True)
            print(f"**[تتبع التقديم]** {interaction.user.display_name} أرسل تقديمًا جديدًا للإدارة.")
        except discord.Forbidden:
            print(f"**[خطأ صلاحيات التقديم]** البوت لا يملك صلاحية إرسال الرسائل في قناة التقديمات ({APPLICATIONS_CHANNEL_ID}).")
            await interaction.response.send_message("❌ لا أمتلك الصلاحية لإرسال تقديمك في قناة التقديمات. يرجى إبلاغ الإدارة.", ephemeral=True)
        except Exception as e:
            print(f"**[خطأ عام في التقديم]** حدث خطأ غير متوقع عند إرسال التقديم: {e}")
            await interaction.response.send_message("❌ حدث خطأ غير متوقع عند محاولة إرسال طلبك. يرجى المحاولة لاحقاً.", ephemeral=True)

@bot.command(name='apply')
async def apply_command(ctx):
    """ يرسل رسالة التقديم مع زر لفتح النموذج (خاص بالمالك). """
    if ctx.author.id != OWNER_ID_FOR_APPLY:
        await ctx.send("❌ عذراً، هذا الأمر مخصص للمالك فقط.", ephemeral=True, delete_after=5)
        return
    # الرسالة باللغة العربية مع الايموجيز التي طلبتها
    embed = discord.Embed(
        title="Revolver | التقديم",
        description="**__التقديـم <:R30:1384226513737748621> __ \n\n"
                    "لتقديـم الى إدارة ريفولفر <:Revolver:1391149572268494928> اضغط على الزر <:R30:1384226513737748621> و اكمل الغراغات . \n"
                    "( عند قبولك كإداري سوف تلحقك رسالة من بوت السيستم <:R8:1384226000795205732> ) \n\n"
                    "<:R22:1384226486541881466><:R22:1384226486541881466><:R22:1384226486541881466> يجب عليك وضع شعار (RV) في اسمك\n"
                    "<:R22:1384226486541881466><:R22:1384226486541881466><:R22:1384226486541881466> الاحترام و الاخلاق و اللباقة\n"
                    "<:R22:1384226486541881466><:R22:1384226486541881466><:R22:1384226486541881466> الخبرة الكافية في إدارة السيرفرات\n"
                    "<:R22:1384226486541881466><:R22:1384226486541881466><:R22:1384226486541881466> تكون متفاعل في السيرفر\n"
                    "<:R22:1384226486541881466><:R22:1384226486541881466><:R22:1384226486541881466> لا تسأل عن حاله الطلب\n"
                    "<:R22:1384226486541881466><:R22:1384226486541881466><:R22:1384226486541881466> عدم ازعاج الادارة\n"
                    "<:R22:1384226486541881466><:R22:1384226486541881466><:R22:1384226486541881466> العمر اكثر من 16\n\n"
                    "**ملاحظة: سيتم تجاهل أي تقديم لا يستوفي الشروط أو لا يحتوي على شعار (RV) في الاسم.**",
        color=0x23c536
    )
    embed.set_image(url="https://i.postimg.cc/85z076B9/16.png") # تم تحديث الصورة هنا
    # الزر الذي يفتح المودال
    apply_button = discord.ui.Button(
        label="تقديم طلب",
        style=discord.ButtonStyle.green,
        emoji="✍️"
    )
    async def apply_button_callback(interaction: discord.Interaction):
        await interaction.response.send_modal(CustomApplyModal())
    apply_button.callback = apply_button_callback
    apply_view = View()
    apply_view.add_item(apply_button)
    await ctx.send(embed=embed, view=apply_view)

# -------------------------------------------------------------
# نهاية أمر !apply
# -------------------------------------------------------------

# -------------------------------------------------------------
# أمر !ticket الجديد
# -------------------------------------------------------------
@bot.command(name='ticket')
@commands.has_role(1331332308745064499) # فقط الأدمن يمكنه إرسال رسالة التذكرة
async def create_ticket_message(ctx):
    """
    يرسل رسالة إعداد نظام التذاكر مع زر "فتح تذكرة".
    """
    embed = discord.Embed(
        title="Revolver | التذكرة",
        description="**__التذكرة <:r5:1385305455471099974> __\n\n"
                    "يمنع السب و الشتم <:R7:1384225997360205884>\n"
                    "إلتزام بقوانين العامة <:R7:1384225997360205884>\n"
                    "عدم منشن بشكل تكراري <:R7:1384225997360205884>\n"
                    "عدم الإستهبال <:R7:1384225997360205884>\n"
                    "الإحترام و تقدير اعمال الإدارة <:R7:1384225997360205884>\n\n"
                    "<:R22:1384226486541881466><:R22:1384226486541881466><:R22:1384226486541881466><:R22:1384226486541881466><:R22:1384226486541881466><:R22:1384226486541881466><:R22:1384226486541881466><:R22:1384226486541881466><:R22:1384226486541881466><:R22:1384226486541881466><:R22:1384226486541881466><:R22:1384226486541881466><:R22:1384226486541881466>\n\n"
                    "لفتح التذكرة اضغط على زر <:r5:1385305455471099974> انتظر و سوف يساعدك أحد الإدارين <@&" + str(STAFF_ROLE_ID) + ">**",
        color=0x23c536
    )
    embed.set_image(url="https://i.postimg.cc/Y034Z1Yp/3.png")

    class TicketView(View):
        def __init__(self):
            super().__init__(timeout=None) # اجعل View يستمر بعد إعادة تشغيل البوت

        @discord.ui.button(label="فتح تذكرة", style=discord.ButtonStyle.gray, emoji="<:r5:1385305455471099974>")
        async def open_ticket_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            member = interaction.user
            guild = interaction.guild

            # التحقق مما إذا كان المستخدم لديه تذكرة مفتوحة بالفعل
            if member.id in open_tickets:
                existing_channel_id = open_tickets[member.id]
                existing_channel = guild.get_channel(existing_channel_id)
                if existing_channel:
                    await interaction.response.send_message(f"لديك بالفعل تذكرة مفتوحة هنا: {existing_channel.mention}", ephemeral=True)
                    return
                else:
                    # إذا كانت القناة غير موجودة في Discord (تم حذفها يدويًا)، فقم بإزالتها من open_tickets
                    del open_tickets[member.id]

            category = bot.get_channel(TICKET_CATEGORY_ID)
            if not category:
                await interaction.response.send_message("❌ حدث خطأ: لا يمكن العثور على فئة التذاكر. يرجى إبلاغ الإدارة.", ephemeral=True)
                print(f"**[خطأ التذاكر]** لم يتم العثور على فئة التذاكر بالـ ID: {TICKET_CATEGORY_ID}")
                return

            # تحديد الصلاحيات للقناة الجديدة
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False), # لا أحد يرى القناة
                member: discord.PermissionOverwrite(read_messages=True, send_messages=True, embed_links=True, attach_files=True), # صاحب التذكرة يرى
                guild.get_role(STAFF_ROLE_ID): discord.PermissionOverwrite(read_messages=True, send_messages=True, embed_links=True, attach_files=True) # الطاقم يرى
            }

            try:
                ticket_channel = await guild.create_text_channel(
                    name=f'ticket-{member.name}-{member.discriminator}',
                    category=category,
                    overwrites=overwrites,
                    topic=f"تذكرة دعم لـ {member.display_name} ({member.id}). تم الإنشاء في {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
                open_tickets[member.id] = ticket_channel.id # تسجيل التذكرة المفتوحة

                await interaction.response.send_message(f"✅ تم إنشاء تذكرتك هنا: {ticket_channel.mention}", ephemeral=True)

                # رسالة الترحيب داخل التذكرة
                ticket_embed = discord.Embed(
                    title="تذكرتك جاهزة!",
                    description=f"{member.mention} هذه تذكرتك. الرجاء وصف مشكلتك وسيقوم أحد الإداريين <@&{STAFF_ROLE_ID}> بالرد عليك قريباً.\n\n"
                                f"لروئية معلومات اكثر توجه <#{PRICES_CHANNEL_ID}> <:R24:1384226493613342793>",
                    color=0x23c536
                )
                
                # أزرار داخل التذكرة
                ticket_buttons_view = View(timeout=None) # اجعل View يستمر
                
                # زر الشراء
                buy_button = discord.ui.Button(label="شراء", style=discord.ButtonStyle.green, emoji="<:RS:1384671817729314826>")
                async def buy_callback(interaction: discord.Interaction):
                    prices_channel = bot.get_channel(PRICES_CHANNEL_ID)
                    if prices_channel:
                        await interaction.response.send_message(f"** لشراء رتب اكتب كلمة <:R15:1384226111428366386>\n`!اشتري`**", ephemeral=True)
                    else:
                        await interaction.response.send_message("قناة الأسعار غير موجودة.", ephemeral=True)
                buy_button.callback = buy_callback
                ticket_buttons_view.add_item(buy_button)

                # زر الاستلام (خاص بالإدارة)
                receive_button = discord.ui.Button(label="استلام", style=discord.ButtonStyle.blurple, emoji="<:R13:1384226102855204864>")
                async def receive_callback(interaction: discord.Interaction):
                    if guild.get_role(STAFF_ROLE_ID) in interaction.user.roles: # التحقق من رتبة الإدارة
                        # إضافة نقاط (يمكنك تغيير القيمة 10 حسب رغبتك)
                        points_to_add = 10
                        points_db[member.id] = points_db.get(member.id, 0) + points_to_add
                        
                        receive_log_channel = bot.get_channel(RECEIVE_LOG_CHANNEL_ID)
                        if receive_log_channel:
                            await receive_log_channel.send(
                                f"**✅ تم منح {points_to_add} نقطة لـ {member.mention} بواسطة {interaction.user.mention} من تذكرة {ticket_channel.mention}.**"
                            )
                        
                        await interaction.response.send_message(f"تم منح {points_to_add} نقطة لـ {member.mention} بنجاح!", ephemeral=True)
                        print(f"**[تتبع التذاكر]** {interaction.user.display_name} منح {points_to_add} نقطة لـ {member.display_name} في تذكرة {ticket_channel.name}.")
                    else:
                        await interaction.response.send_message("❌ ليس لديك الصلاحية لاستخدام هذا الزر.", ephemeral=True)

                receive_button.callback = receive_callback
                ticket_buttons_view.add_item(receive_button)
                
                # زر الإغلاق
                close_button = discord.ui.Button(label="إغلاق", style=discord.ButtonStyle.red, emoji="<:RS:1384671819994366082>")
                async def close_callback(interaction: discord.Interaction):
                    # تأكيد الإغلاق
                    confirm_view = View()
                    confirm_button_yes = discord.ui.Button(label="نعم، أغلق", style=discord.ButtonStyle.red)
                    confirm_button_no = discord.ui.Button(label="لا، إلغاء", style=discord.ButtonStyle.gray)

                    async def confirm_yes_callback(confirm_interaction: discord.Interaction):
                        try:
                            # تسجيل الإغلاق في لوج التذاكر
                            log_channel = bot.get_channel(TICKET_LOG_CHANNEL_ID)
                            if log_channel:
                                log_embed = discord.Embed(
                                    title="تم إغلاق تذكرة",
                                    description=f"**فاتح التذكرة:** {member.mention} (`{member.id}`)\n"
                                                f"**القناة:** `{ticket_channel.name}` (`{ticket_channel.id}`)\n"
                                                f"**المُغلق بواسطة:** {confirm_interaction.user.mention} (`{confirm_interaction.user.id}`)\n"
                                                f"**تاريخ الإغلاق:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                                    color=discord.Color.red(),
                                    timestamp=datetime.now()
                                )
                                await log_channel.send(embed=log_embed)
                                print(f"**[تتبع التذاكر]** تم تسجيل إغلاق التذكرة {ticket_channel.name} بواسطة {confirm_interaction.user.display_name}.")

                            await ticket_channel.delete()
                            if member.id in open_tickets:
                                del open_tickets[member.id]
                            await confirm_interaction.response.send_message("تم إغلاق التذكرة بنجاح.", ephemeral=True)
                            print(f"**[تتبع التذاكر]** تم حذف قناة التذكرة: {ticket_channel.name}.")
                        except discord.Forbidden:
                            await confirm_interaction.response.send_message("❌ ليس لدي صلاحية حذف هذه القناة.", ephemeral=True)
                            print(f"**[خطأ صلاحيات التذاكر]** البوت لا يملك صلاحية حذف القناة {ticket_channel.name}.")
                        except Exception as e:
                            await confirm_interaction.response.send_message(f"❌ حدث خطأ عند إغلاق التذكرة: {str(e)}", ephemeral=True)
                            print(f"**[خطأ عام في التذاكر]** حدث خطأ عند إغلاق التذكرة {ticket_channel.name}: {e}")

                    async def confirm_no_callback(confirm_interaction: discord.Interaction):
                        await confirm_interaction.response.send_message("تم إلغاء إغلاق التذكرة.", ephemeral=True)
                    
                    confirm_button_yes.callback = confirm_yes_callback
                    confirm_button_no.callback = confirm_no_callback
                    confirm_view.add_item(confirm_button_yes)
                    confirm_view.add_item(confirm_button_no)

                    await interaction.response.send_message("هل أنت متأكد من رغبتك في إغلاق التذكرة؟", view=confirm_view, ephemeral=True)

                close_button.callback = close_callback
                ticket_buttons_view.add_item(close_button)

                await ticket_channel.send(embed=ticket_embed, view=ticket_buttons_view)
                print(f"**[تتبع التذاكر]** تم إنشاء تذكرة جديدة: {ticket_channel.name} بواسطة {member.display_name}.")

            except discord.Forbidden:
                await interaction.response.send_message("❌ ليس لدي الصلاحية لإنشاء قنوات أو تعيين الصلاحيات. يرجى التأكد من صلاحياتي.", ephemeral=True)
                print(f"**[خطأ صلاحيات التذاكر]** البوت لا يملك صلاحية إنشاء قنوات أو تعيين صلاحيات في السيرفر.")
            except Exception as e:
                await interaction.response.send_message(f"❌ حدث خطأ غير متوقع عند فتح التذكرة: {str(e)}. يرجى إبلاغ الإدارة.", ephemeral=True)
                print(f"**[خطأ عام في التذاكر]** حدث خطأ غير متوقع عند إنشاء تذكرة: {e}")

    try:
        await ctx.message.delete()
        await ctx.send(embed=embed, view=TicketView())
        print(f"**تتبع (!ticket):** تم إرسال رسالة نظام التذاكر بواسطة {ctx.author.name} في {ctx.channel.name}")
    except discord.Forbidden:
        print(f"**خطأ (!ticket):** البوت لا يملك صلاحية حذف الرسائل أو إرسالها في القناة {ctx.channel.name}.")
        await ctx.send("❌ لا أمتلك الصلاحيات اللازمة لحذف رسالتك أو إرسال رسالة التذاكر هنا. يرجى مراجعة صلاحياتي.", delete_after=10)
    except Exception as e:
        print(f"**خطأ (!ticket):** حدث خطأ غير متوقع عند إرسال رسالة التذاكر: {e}")
        await ctx.send("❌ حدث خطأ غير متوقع عند محاولة إرسال رسالة التذاكر.", delete_after=10)

# -------------------------------------------------------------
# نهاية أمر !ticket
# -------------------------------------------------------------


bot.run("MTMxNjEwODA4MDg3ODA2MzY3OQ.Gr47C6.VKhpPkKcGDifpXyNbJACpVoKxAghX9cWIPEXOI") # استبدل بـ توكن البوت الخاص بك
