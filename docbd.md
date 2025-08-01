📊 ПОВНА ДОКУМЕНТАЦІЯ БАЗИ ДАНИХ TELEBOOST
==========================================

📋 ЗМІСТ
--------

1. [Загальна інформація](#загальна-інформація)
2. [ENUM типи](#enum-типи)
3. [Таблиці](#таблиці)
4. [Функції](#функції)
5. [Тригери](#тригери)
6. [Row Level Security](#row-level-security)
7. [Індекси](#індекси)
8. [Зв'язки між таблицями](#звязки-між-таблицями)
9. [Виклик RPC функцій з Python](#виклик-rpc-функцій-з-python)
10. [Приклади запитів](#приклади-запитів)
11. [Оптимізація та Best Practices](#оптимізація-та-best-practices)
12. [Maintenance](#maintenance)

🌐 ЗАГАЛЬНА ІНФОРМАЦІЯ
--------------------

### Технології
- **База даних**: PostgreSQL (Supabase)
- **Розширення**: uuid-ossp, pgcrypto
- **Часова зона**: UTC
- **Row Level Security**: Enabled для всіх таблиць

### Архітектура
База даних складається з 8 основних таблиць, що забезпечують функціонал:
- Управління користувачами та авторизація
- Реферальна система (дворівнева: 7% для L1, 2.5% для L2)
- Управління сервісами та замовленнями
- Платіжна система
- Транзакції та баланси
- Аналітика та статистика

🎯 ENUM ТИПИ
-----------

### order_status
```sql
CREATE TYPE order_status AS ENUM (
    'pending',       -- Очікує обробки
    'processing',    -- Обробляється
    'in_progress',   -- Виконується
    'completed',     -- Завершено
    'partial',       -- Частково виконано
    'cancelled',     -- Скасовано
    'failed'         -- Помилка
);
```

### payment_status
```sql
CREATE TYPE payment_status AS ENUM (
    'waiting',       -- Очікує оплати
    'confirming',    -- Підтверджується
    'confirmed',     -- Підтверджено
    'sending',       -- Відправляється
    'partially_paid',-- Частково оплачено
    'finished',      -- Завершено
    'failed',        -- Помилка
    'refunded',      -- Повернено
    'expired'        -- Прострочено
);
```

### transaction_type
```sql
CREATE TYPE transaction_type AS ENUM (
    'deposit',       -- Поповнення
    'withdraw',      -- Виведення
    'order',         -- Замовлення
    'refund',        -- Повернення
    'referral_bonus',-- Реферальний бонус
    'cashback',      -- Кешбек
    'admin_credit',  -- Адмін нарахування
    'admin_debit'    -- Адмін списання
);
```

### payment_provider
```sql
CREATE TYPE payment_provider AS ENUM (
    'cryptobot',     -- CryptoBot
    'nowpayments',   -- NOWPayments
    'monobank'       -- Monobank
);
```

📁 ТАБЛИЦІ
---------

### 1️⃣ users - Користувачі
```sql
CREATE TABLE users (
    -- Ідентифікатори
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    telegram_id TEXT UNIQUE NOT NULL,
    
    -- Основна інформація
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    language_code TEXT DEFAULT 'en',
    is_premium BOOLEAN DEFAULT false,
    is_admin BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    
    -- Баланс та фінанси
    balance DECIMAL(15,2) DEFAULT 0.00 CHECK (balance >= 0),
    total_deposited DECIMAL(15,2) DEFAULT 0.00,
    total_withdrawn DECIMAL(15,2) DEFAULT 0.00,
    total_spent DECIMAL(15,2) DEFAULT 0.00,
    
    -- Реферальна система
    referral_code TEXT UNIQUE,
    referred_by UUID REFERENCES users(id),
    referral_earnings DECIMAL(15,2) DEFAULT 0.00,
    
    -- Часові мітки
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_login TIMESTAMPTZ,
    
    -- Додаткові дані
    photo_url TEXT,
    settings JSONB DEFAULT '{}'
);
```

### 2️⃣ user_sessions - Сесії користувачів
```sql
CREATE TABLE user_sessions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- JWT токени
    access_token_jti TEXT UNIQUE NOT NULL,
    refresh_token_jti TEXT UNIQUE NOT NULL,
    
    -- Інформація про сесію
    ip_address TEXT,
    user_agent TEXT,
    
    -- Часові мітки
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    is_active BOOLEAN DEFAULT true
);
```

### 3️⃣ services - Сервіси
```sql
CREATE TABLE services (
    -- Використовуємо Nakrutochka ID як primary key
    id INTEGER PRIMARY KEY,
    
    -- Основна інформація
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    category TEXT NOT NULL,
    
    -- Ціноутворення
    rate DECIMAL(15,4) NOT NULL,  -- Ціна за 1000
    min INTEGER NOT NULL,
    max INTEGER NOT NULL,
    
    -- Можливості
    dripfeed BOOLEAN DEFAULT false,
    refill BOOLEAN DEFAULT false,
    cancel BOOLEAN DEFAULT false,
    
    -- Додаткова інформація
    description TEXT,
    position INTEGER DEFAULT 999,
    tags TEXT[] DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    
    -- Статус
    status TEXT DEFAULT 'active',
    is_active BOOLEAN DEFAULT true,
    
    -- Часові мітки
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 4️⃣ orders - Замовлення
```sql
CREATE TABLE orders (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Зв'язок з Nakrutochka
    nakrutochka_order_id TEXT UNIQUE,
    service_id INTEGER NOT NULL REFERENCES services(id),
    
    -- Деталі замовлення
    link TEXT NOT NULL,
    quantity INTEGER,
    comments TEXT,
    
    -- Фінанси та статус
    charge DECIMAL(15,2) NOT NULL,
    remains INTEGER DEFAULT 0,
    start_count INTEGER DEFAULT 0,
    status order_status NOT NULL DEFAULT 'pending',
    
    -- Часові мітки
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Додаткові дані
    metadata JSONB DEFAULT '{}'
);
```

### 5️⃣ payments - Платежі
```sql
CREATE TABLE payments (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Ідентифікація платежу
    payment_id TEXT UNIQUE NOT NULL,
    provider payment_provider NOT NULL,
    
    -- Деталі платежу
    type TEXT NOT NULL CHECK (type IN ('deposit', 'withdraw')),
    amount DECIMAL(15,2) NOT NULL,
    currency TEXT NOT NULL,
    status payment_status NOT NULL DEFAULT 'waiting',
    
    -- Додаткова інформація
    payment_url TEXT,
    expires_at TIMESTAMPTZ,
    paid_at TIMESTAMPTZ,
    
    -- Часові мітки
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Метадані від провайдера
    metadata JSONB DEFAULT '{}'
);
```

### 6️⃣ transactions - Транзакції
```sql
CREATE TABLE transactions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Деталі транзакції
    type transaction_type NOT NULL,
    amount DECIMAL(15,2) NOT NULL,
    
    -- Баланс до і після
    balance_before DECIMAL(15,2) NOT NULL,
    balance_after DECIMAL(15,2) NOT NULL,
    
    -- Опис та додаткові дані
    description TEXT,
    metadata JSONB DEFAULT '{}',
    
    -- Часова мітка
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 7️⃣ referrals - Реферали (ДВОРІВНЕВА СИСТЕМА)
```sql
CREATE TABLE referrals (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    
    -- Зв'язки
    referrer_id UUID NOT NULL REFERENCES users(id),
    referred_id UUID NOT NULL REFERENCES users(id),
    
    -- Рівень реферала (1 або 2)
    level INTEGER NOT NULL DEFAULT 1 CHECK (level IN (1, 2)),
    
    -- Фінанси
    bonus_paid BOOLEAN DEFAULT false,
    bonus_amount DECIMAL(15,2) DEFAULT 0,
    total_deposits DECIMAL(15,2) DEFAULT 0.00,
    total_bonuses_generated DECIMAL(15,2) DEFAULT 0.00,
    
    -- Статус
    is_active BOOLEAN DEFAULT true,
    
    -- Часові мітки
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_deposit_at TIMESTAMPTZ,
    
    -- Унікальність зв'язку
    UNIQUE(referrer_id, referred_id)
);
```

### 8️⃣ bot_stats - Статистика бота
```sql
CREATE TABLE bot_stats (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    
    -- Статистика
    user_count INTEGER DEFAULT 0,
    order_count INTEGER DEFAULT 0,
    total_revenue DECIMAL(15,2) DEFAULT 0,
    
    -- Дата статистики
    date DATE UNIQUE NOT NULL,
    
    -- Часові мітки
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

🔧 ФУНКЦІЇ
---------

### increment_balance - Збільшення балансу
```sql
CREATE OR REPLACE FUNCTION increment_balance(
    user_id UUID,
    amount DECIMAL
) RETURNS BOOLEAN AS $$
DECLARE
    current_balance DECIMAL;
    new_balance DECIMAL;
BEGIN
    -- Блокуємо рядок для оновлення
    SELECT balance INTO current_balance
    FROM users
    WHERE id = user_id
    FOR UPDATE;
    
    IF current_balance IS NULL THEN
        RETURN FALSE;
    END IF;
    
    new_balance := current_balance + amount;
    
    -- Перевіряємо чи не буде від'ємний баланс
    IF new_balance < 0 THEN
        RETURN FALSE;
    END IF;
    
    UPDATE users
    SET balance = new_balance,
        updated_at = NOW()
    WHERE id = user_id;
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

### decrement_balance - Зменшення балансу
```sql
CREATE OR REPLACE FUNCTION decrement_balance(
    user_id UUID,
    amount DECIMAL
) RETURNS BOOLEAN AS $$
BEGIN
    RETURN increment_balance(user_id, -amount);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

### increment_value - Універсальна функція інкременту
```sql
CREATE OR REPLACE FUNCTION increment_value(
    table_name TEXT,
    column_name TEXT,
    row_id UUID,
    increment_by DECIMAL
) RETURNS BOOLEAN AS $$
DECLARE
    query TEXT;
    rows_updated INTEGER;
BEGIN
    -- Формуємо динамічний запит
    query := format('UPDATE %I SET %I = COALESCE(%I, 0) + $1 WHERE id = $2', 
                    table_name, column_name, column_name);
    
    -- Виконуємо запит
    EXECUTE query USING increment_by, row_id;
    
    -- Перевіряємо чи був оновлений рядок
    GET DIAGNOSTICS rows_updated = ROW_COUNT;
    
    RETURN rows_updated > 0;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

### update_updated_at_column - Оновлення updated_at
```sql
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

⚡ ТРИГЕРИ
---------

### Автоматичне оновлення updated_at
```sql
CREATE TRIGGER update_users_updated_at 
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_orders_updated_at 
    BEFORE UPDATE ON orders
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_payments_updated_at 
    BEFORE UPDATE ON payments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_services_updated_at 
    BEFORE UPDATE ON services
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_bot_stats_updated_at 
    BEFORE UPDATE ON bot_stats
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

🔒 ROW LEVEL SECURITY
-------------------

### Політики для таблиці users
```sql
-- Користувачі можуть бачити свій профіль, адміни - всіх
CREATE POLICY "Users can view own profile" ON users
    FOR SELECT USING (auth.uid()::text = id::text OR is_admin = true);

-- Користувачі можуть оновлювати свій профіль
CREATE POLICY "Users can update own profile" ON users
    FOR UPDATE USING (auth.uid()::text = id::text);
```

### Політики для інших таблиць
```sql
-- Транзакції
CREATE POLICY "Users can view own transactions" ON transactions
    FOR SELECT USING (auth.uid()::text = user_id::text);

-- Замовлення
CREATE POLICY "Users can view own orders" ON orders
    FOR SELECT USING (auth.uid()::text = user_id::text);

-- Платежі
CREATE POLICY "Users can view own payments" ON payments
    FOR SELECT USING (auth.uid()::text = user_id::text);

-- Реферали
CREATE POLICY "Users can view own referrals" ON referrals
    FOR SELECT USING (auth.uid()::text = referrer_id::text);

-- Сервіси (публічний доступ)
CREATE POLICY "Anyone can view active services" ON services
    FOR SELECT USING (is_active = true);

-- Статистика (тільки адміни)
CREATE POLICY "Only admins can view stats" ON bot_stats
    FOR SELECT USING (EXISTS (
        SELECT 1 FROM users WHERE id::text = auth.uid()::text AND is_admin = true
    ));
```

📊 ІНДЕКСИ
---------

### Таблиця users
```sql
CREATE INDEX idx_users_telegram_id ON users(telegram_id);
CREATE INDEX idx_users_referral_code ON users(referral_code);
CREATE INDEX idx_users_referred_by ON users(referred_by);
CREATE INDEX idx_users_created_at ON users(created_at DESC);
```

### Таблиця user_sessions
```sql
CREATE INDEX idx_sessions_user_id ON user_sessions(user_id);
CREATE INDEX idx_sessions_expires_at ON user_sessions(expires_at);
CREATE INDEX idx_sessions_active ON user_sessions(is_active);
```

### Таблиця services
```sql
CREATE INDEX idx_services_category ON services(category);
CREATE INDEX idx_services_type ON services(type);
CREATE INDEX idx_services_active ON services(is_active);
CREATE INDEX idx_services_position ON services(position);
```

### Таблиця orders
```sql
CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_created_at ON orders(created_at DESC);
CREATE INDEX idx_orders_nakrutochka_id ON orders(nakrutochka_order_id);
```

### Таблиця payments
```sql
CREATE INDEX idx_payments_user_id ON payments(user_id);
CREATE INDEX idx_payments_payment_id ON payments(payment_id);
CREATE INDEX idx_payments_status ON payments(status);
CREATE INDEX idx_payments_created_at ON payments(created_at DESC);
```

### Таблиця transactions
```sql
CREATE INDEX idx_transactions_user_id ON transactions(user_id);
CREATE INDEX idx_transactions_type ON transactions(type);
CREATE INDEX idx_transactions_created_at ON transactions(created_at DESC);
```

### Таблиця referrals
```sql
CREATE INDEX idx_referrals_referrer ON referrals(referrer_id);
CREATE INDEX idx_referrals_referred ON referrals(referred_id);
CREATE INDEX idx_referrals_level ON referrals(level);
CREATE INDEX idx_referrals_is_active ON referrals(is_active);
```

### Таблиця bot_stats
```sql
CREATE INDEX idx_bot_stats_date ON bot_stats(date);
```

🔗 ЗВ'ЯЗКИ МІЖ ТАБЛИЦЯМИ
----------------------

### Діаграма зв'язків
```
users
  ├── user_sessions (user_id)
  ├── orders (user_id)
  ├── payments (user_id)
  ├── transactions (user_id)
  ├── referrals (referrer_id, referred_id)
  └── users (referred_by) [self-reference]

services
  └── orders (service_id)

referrals (дворівнева система)
  ├── level 1: прямі реферали (7% бонус)
  └── level 2: реферали рефералів (2.5% бонус)
```

🐍 ВИКЛИК RPC ФУНКЦІЙ З PYTHON
-----------------------------

### ⚠️ ВАЖЛИВО: Різниця між SQL та Python

При використанні **Supabase Python клієнта**, RPC функції викликаються через словник параметрів, а не напряму як в SQL:

### Приклади для Python

#### increment_balance
```python
# ❌ НЕПРАВИЛЬНО - це SQL синтаксис
# supabase.rpc('increment_balance', user_id, amount)

# ✅ ПРАВИЛЬНО - Python синтаксис
result = supabase.client.rpc('increment_balance', {
    'user_id': 'uuid-here',
    'amount': 100.00
}).execute()

# Перевірка результату
if result.data is True:
    print("Баланс успішно оновлено")
```

#### decrement_balance
```python
result = supabase.client.rpc('decrement_balance', {
    'user_id': 'uuid-here',
    'amount': 50.00
}).execute()

if result.data is True:
    print("Кошти успішно списані")
```

#### increment_value
```python
# Оновлення total_deposits в таблиці referrals
result = supabase.client.rpc('increment_value', {
    'table_name': 'referrals',
    'column_name': 'total_deposits',
    'row_id': 'referral-uuid-here',
    'increment_by': 150.00
}).execute()

# Оновлення referral_earnings в таблиці users
result = supabase.client.rpc('increment_value', {
    'table_name': 'users',
    'column_name': 'referral_earnings',
    'row_id': 'user-uuid-here',
    'increment_by': 10.50
}).execute()
```

### Обробка помилок в Python
```python
try:
    result = supabase.client.rpc('increment_balance', {
        'user_id': user_id,
        'amount': amount
    }).execute()
    
    if result.data is True:
        print("Успішно!")
    else:
        print("Операція не вдалася")
        
except Exception as e:
    print(f"Помилка: {e}")
```

💡 ПРИКЛАДИ ЗАПИТІВ
-----------------

### Створення користувача з реферальним кодом

#### SQL версія:
```sql
-- Створення нового користувача
INSERT INTO users (telegram_id, username, first_name, referral_code, referred_by)
VALUES ('123456789', 'newuser', 'John', 'REF123456', 
    (SELECT id FROM users WHERE referral_code = 'REFERRER_CODE'))
RETURNING *;

-- Створення реферального зв'язку
INSERT INTO referrals (referrer_id, referred_id, level)
VALUES (
    (SELECT id FROM users WHERE referral_code = 'REFERRER_CODE'),
    (SELECT id FROM users WHERE telegram_id = '123456789'),
    1
);
```

#### Python версія:
```python
# Створення користувача
user_data = {
    'telegram_id': '123456789',
    'username': 'newuser',
    'first_name': 'John',
    'referral_code': 'REF123456',
    'referred_by': referrer_id  # UUID реферера
}
user = supabase.create_user(user_data)

# Створення реферального зв'язку
referral_data = {
    'referrer_id': referrer_id,
    'referred_id': user['id'],
    'level': 1
}
supabase.create_referral(referrer_id, user['id'], level=1)
```

### Поповнення балансу

#### SQL версія:
```sql
-- Використання функції increment_balance
SELECT increment_balance('user_id_here'::uuid, 100.00);

-- Створення транзакції
INSERT INTO transactions (user_id, type, amount, balance_before, balance_after, description)
VALUES (
    'user_id_here'::uuid,
    'deposit',
    100.00,
    (SELECT balance FROM users WHERE id = 'user_id_here'::uuid),
    (SELECT balance + 100.00 FROM users WHERE id = 'user_id_here'::uuid),
    'Поповнення через CryptoBot'
);
```

#### Python версія:
```python
# Оновлення балансу
balance_updated = supabase.update_user_balance(user_id, 100.00, operation='add')

if balance_updated:
    # Створення транзакції
    transaction_data = {
        'user_id': user_id,
        'type': 'deposit',
        'amount': 100.00,
        'balance_before': current_balance,
        'balance_after': current_balance + 100.00,
        'description': 'Поповнення через CryptoBot'
    }
    supabase.create_transaction(transaction_data)
```

### Нарахування реферального бонусу

#### Дворівнева система:
- **Рівень 1**: 7% від депозиту для прямого реферера
- **Рівень 2**: 2.5% від депозиту для реферера реферера

#### Python реалізація:
```python
# Нарахування бонусу першого рівня (7%)
deposit_amount = 1000.00
level1_bonus = deposit_amount * 0.07  # 70.00

# Оновлення балансу реферера
supabase.client.rpc('increment_balance', {
    'user_id': referrer_id,
    'amount': level1_bonus
}).execute()

# Оновлення статистики рефералів
supabase.client.rpc('increment_value', {
    'table_name': 'referrals',
    'column_name': 'total_bonuses_generated',
    'row_id': referral_id,
    'increment_by': level1_bonus
}).execute()

# Нарахування бонусу другого рівня (2.5%)
level2_bonus = deposit_amount * 0.025  # 25.00
# ... аналогічно для реферера другого рівня
```

### Отримання дерева рефералів
```sql
-- Рефералі першого рівня з детальною інформацією
SELECT 
    u.id,
    u.telegram_id,
    u.username,
    r.total_deposits,
    r.total_bonuses_generated,
    r.created_at
FROM referrals r
JOIN users u ON u.id = r.referred_id
WHERE r.referrer_id = 'user_id'::uuid 
AND r.level = 1
AND r.is_active = true;

-- Рефералі другого рівня
SELECT 
    u.id,
    u.telegram_id,
    u.username,
    r.total_deposits,
    r.total_bonuses_generated,
    r.created_at
FROM referrals r
JOIN users u ON u.id = r.referred_id
WHERE r.referrer_id = 'user_id'::uuid 
AND r.level = 2
AND r.is_active = true;
```

### Статистика для адміна
```sql
-- Загальна статистика
SELECT 
    (SELECT COUNT(*) FROM users) as total_users,
    (SELECT COUNT(*) FROM users WHERE created_at > NOW() - INTERVAL '24 hours') as new_users_24h,
    (SELECT COUNT(*) FROM orders) as total_orders,
    (SELECT SUM(charge) FROM orders WHERE status = 'completed') as total_revenue,
    (SELECT SUM(balance) FROM users) as total_user_balance;

-- Топ рефереріів
SELECT 
    u.telegram_id,
    u.username,
    u.referral_earnings,
    COUNT(DISTINCT r1.referred_id) as level1_count,
    COUNT(DISTINCT r2.referred_id) as level2_count,
    SUM(r1.total_bonuses_generated) + COALESCE(SUM(r2.total_bonuses_generated), 0) as total_generated
FROM users u
LEFT JOIN referrals r1 ON r1.referrer_id = u.id AND r1.level = 1
LEFT JOIN referrals r2 ON r2.referrer_id = u.id AND r2.level = 2
GROUP BY u.id
ORDER BY total_generated DESC
LIMIT 10;
```

🚀 ОПТИМІЗАЦІЯ ТА BEST PRACTICES
-------------------------------

### 1. Використання транзакцій
```sql
BEGIN;
    -- Оновлюємо баланс
    SELECT increment_balance('user_id'::uuid, 100.00);
    
    -- Створюємо запис транзакції
    INSERT INTO transactions (...) VALUES (...);
    
    -- Оновлюємо статистику
    UPDATE users SET total_deposited = total_deposited + 100.00 WHERE id = 'user_id';
COMMIT;
```

### 2. Використання prepared statements
```sql
PREPARE get_user_balance AS
    SELECT balance FROM users WHERE telegram_id = $1;

EXECUTE get_user_balance('123456789');
```

### 3. Партиціонування великих таблиць
```sql
-- Для таблиці transactions можна зробити партиціонування по місяцях
CREATE TABLE transactions_2024_01 PARTITION OF transactions
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
```

### 4. Моніторинг продуктивності
```sql
-- Повільні запити
SELECT query, mean_exec_time, calls 
FROM pg_stat_statements 
ORDER BY mean_exec_time DESC 
LIMIT 10;

-- Використання індексів
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
ORDER BY idx_scan;
```

📋 ИЗМЕНЕНИЯ В БАЗЕ ДАННЫХ - ДОКУМЕНТАЦИЯ
🔧 НОВЫЕ ФУНКЦИИ ДЛЯ ДОБАВЛЕНИЯ В SUPABASE:
1. process_referral_bonus - Транзакционная обработка реферальных бонусов
sqlCREATE OR REPLACE FUNCTION process_referral_bonus(
    p_referrer_id UUID,
    p_amount NUMERIC,
    p_referred_user_id UUID,
    p_deposit_amount NUMERIC,
    p_level INTEGER
)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
-- Функция атомарно обрабатывает:
-- 1. Обновление баланса пользователя
-- 2. Обновление referral_earnings
-- 3. Создание транзакции
-- 4. Обновление статистики в таблице referrals
-- Все операции выполняются в одной транзакции
$$;
Назначение: Обеспечивает атомарность операций при начислении реферальных бонусов, предотвращая несоответствие данных при сбоях.
📊 СУЩЕСТВУЮЩИЕ ФУНКЦИИ (уже есть в БД):

increment_value ✅

Универсальная функция для инкремента любых числовых полей
Используется для обновления total_deposits, total_bonuses_generated, referral_earnings


increment_balance / decrement_balance ✅

Безопасное обновление баланса пользователей
Проверка на отрицательный баланс


update_order_status ✅

Обновление статуса заказов с валидацией переходов


update_updated_at_column ✅

Триггерная функция для автоматического обновления updated_at



🗄️ СТРУКТУРА ТАБЛИЦ (подтверждено):
users

referral_earnings (numeric) ✅ - общий заработок с рефералов

referrals

total_deposits (numeric) ✅ - сумма депозитов реферала
total_bonuses_generated (numeric) ✅ - сумма сгенерированных бонусов
last_deposit_at (timestamp with time zone) ✅ - дата последнего депозита

services

id (integer) ✅ - используется как primary key (Nakrutochka ID)

📌 ВАЖЛИВІ ПРИМІТКИ
-----------------

1. **Баланс користувача** - завжди використовуйте функції increment_balance/decrement_balance для атомарних операцій
2. **Реферальна система** - дворівнева (7% для першого рівня, 2.5% для другого)
3. **Service ID** - використовується Nakrutochka service ID (INTEGER) як primary key
4. **Часові зони** - всі часові мітки зберігаються в UTC
5. **Row Level Security** - увімкнена для всіх таблиць, користувачі бачать тільки свої дані
6. **Soft delete** - для користувачів використовується поле is_active замість видалення
7. **Python RPC** - завжди передавайте параметри як словник при виклику з Python клієнта

🔧 MAINTENANCE
-------------

### Backup
```bash
# Створення бекапу
pg_dump -h db.supabase.co -U postgres -d postgres > backup.sql

# Відновлення з бекапу
psql -h db.supabase.co -U postgres -d postgres < backup.sql
```

-- supabase/functions/statistics_functions.sql
-- SQL функції для статистики та аналітики

-- Функція для розрахунку статистики користувача
CREATE OR REPLACE FUNCTION calculate_user_stats(p_user_id UUID)
RETURNS TABLE (
    total_orders INTEGER,
    successful_orders INTEGER,
    failed_orders INTEGER,
    average_order_value NUMERIC,
    lifetime_value NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*)::INTEGER as total_orders,
        COUNT(CASE WHEN status = 'completed' THEN 1 END)::INTEGER as successful_orders,
        COUNT(CASE WHEN status = 'failed' THEN 1 END)::INTEGER as failed_orders,
        COALESCE(AVG(charge), 0)::NUMERIC as average_order_value,
        COALESCE(SUM(charge), 0)::NUMERIC as lifetime_value
    FROM orders
    WHERE user_id = p_user_id;
END;
$$ LANGUAGE plpgsql;

-- Функція для отримання топ користувачів по витратах
CREATE OR REPLACE FUNCTION get_top_spenders(limit_count INTEGER DEFAULT 10)
RETURNS TABLE (
    user_id UUID,
    username VARCHAR,
    total_spent NUMERIC,
    orders_count INTEGER,
    avg_order_value NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        u.id as user_id,
        u.username,
        COALESCE(SUM(o.charge), 0)::NUMERIC as total_spent,
        COUNT(o.id)::INTEGER as orders_count,
        COALESCE(AVG(o.charge), 0)::NUMERIC as avg_order_value
    FROM users u
    LEFT JOIN orders o ON u.id = o.user_id AND o.status = 'completed'
    GROUP BY u.id, u.username
    HAVING COUNT(o.id) > 0
    ORDER BY total_spent DESC
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- Функція для отримання топ користувачів за період
CREATE OR REPLACE FUNCTION get_top_spenders_for_period(
    start_date TIMESTAMP,
    end_date TIMESTAMP,
    limit_count INTEGER DEFAULT 10
)
RETURNS TABLE (
    user_id UUID,
    username VARCHAR,
    total_spent NUMERIC,
    orders_count INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        u.id as user_id,
        u.username,
        COALESCE(SUM(o.charge), 0)::NUMERIC as total_spent,
        COUNT(o.id)::INTEGER as orders_count
    FROM users u
    INNER JOIN orders o ON u.id = o.user_id 
    WHERE o.status = 'completed'
        AND o.created_at >= start_date
        AND o.created_at <= end_date
    GROUP BY u.id, u.username
    ORDER BY total_spent DESC
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- Функція для отримання топ сервісів
CREATE OR REPLACE FUNCTION get_top_services(limit_count INTEGER DEFAULT 10)
RETURNS TABLE (
    service_id INTEGER,
    service_name VARCHAR,
    orders_count INTEGER,
    total_revenue NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        o.service_id,
        COALESCE(o.metadata->>'service_name', 'Unknown Service')::VARCHAR as service_name,
        COUNT(*)::INTEGER as orders_count,
        SUM(o.charge)::NUMERIC as total_revenue
    FROM orders o
    WHERE o.status = 'completed'
    GROUP BY o.service_id, o.metadata->>'service_name'
    ORDER BY total_revenue DESC
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- Функція для отримання топ сервісів за період
CREATE OR REPLACE FUNCTION get_top_services_for_period(
    start_date TIMESTAMP,
    end_date TIMESTAMP,
    limit_count INTEGER DEFAULT 10
)
RETURNS TABLE (
    service_id INTEGER,
    service_name VARCHAR,
    orders_count INTEGER,
    total_revenue NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        o.service_id,
        COALESCE(o.metadata->>'service_name', 'Unknown Service')::VARCHAR as service_name,
        COUNT(*)::INTEGER as orders_count,
        SUM(o.charge)::NUMERIC as total_revenue
    FROM orders o
    WHERE o.status = 'completed'
        AND o.created_at >= start_date
        AND o.created_at <= end_date
    GROUP BY o.service_id, o.metadata->>'service_name'
    ORDER BY total_revenue DESC
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- Функція для отримання топ рефереров
CREATE OR REPLACE FUNCTION get_top_referrers(limit_count INTEGER DEFAULT 10)
RETURNS TABLE (
    referrer_id UUID,
    username VARCHAR,
    referrals_count INTEGER,
    total_earnings NUMERIC,
    active_referrals INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        u.id as referrer_id,
        u.username,
        COUNT(r.id)::INTEGER as referrals_count,
        u.referral_earnings as total_earnings,
        COUNT(CASE WHEN r.is_active THEN 1 END)::INTEGER as active_referrals
    FROM users u
    LEFT JOIN referrals r ON u.id = r.referrer_id
    WHERE u.referral_earnings > 0
    GROUP BY u.id, u.username, u.referral_earnings
    ORDER BY u.referral_earnings DESC
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- Функція для розрахунку середньої вартості замовлення
CREATE OR REPLACE FUNCTION calculate_average_order_value()
RETURNS NUMERIC AS $$
BEGIN
    RETURN (
        SELECT COALESCE(AVG(charge), 0)::NUMERIC
        FROM orders
        WHERE status = 'completed'
    );
END;
$$ LANGUAGE plpgsql;

-- Функція для інкрементування значення в таблиці
CREATE OR REPLACE FUNCTION increment_value(
    table_name TEXT,
    column_name TEXT,
    row_id UUID,
    increment_by NUMERIC
)
RETURNS BOOLEAN AS $$
DECLARE
    query TEXT;
    result_count INTEGER;
BEGIN
    -- Безпечна побудова запиту з валідацією імен
    IF table_name NOT IN ('users', 'referrals', 'orders') THEN
        RAISE EXCEPTION 'Invalid table name';
    END IF;
    
    IF column_name NOT IN ('balance', 'total_spent', 'total_deposits', 'total_bonuses_generated', 'referral_earnings') THEN
        RAISE EXCEPTION 'Invalid column name';
    END IF;
    
    -- Виконуємо оновлення
    query := format(
        'UPDATE %I SET %I = COALESCE(%I, 0) + $1 WHERE id = $2',
        table_name,
        column_name,
        column_name
    );
    
    EXECUTE query USING increment_by, row_id;
    
    GET DIAGNOSTICS result_count = ROW_COUNT;
    
    RETURN result_count > 0;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Функція для декрементування балансу (з перевіркою)
CREATE OR REPLACE FUNCTION decrement_balance(
    user_id UUID,
    amount NUMERIC
)
RETURNS BOOLEAN AS $$
DECLARE
    current_balance NUMERIC;
BEGIN
    -- Отримуємо поточний баланс з блокуванням
    SELECT balance INTO current_balance
    FROM users
    WHERE id = user_id
    FOR UPDATE;
    
    -- Перевіряємо достатність коштів
    IF current_balance IS NULL OR current_balance < amount THEN
        RETURN FALSE;
    END IF;
    
    -- Оновлюємо баланс
    UPDATE users
    SET balance = balance - amount
    WHERE id = user_id;
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- Функція для інкрементування балансу
CREATE OR REPLACE FUNCTION increment_balance(
    user_id UUID,
    amount NUMERIC
)
RETURNS BOOLEAN AS $$
BEGIN
    UPDATE users
    SET balance = COALESCE(balance, 0) + amount
    WHERE id = user_id;
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- Функція для обробки реферального бонусу в транзакції
CREATE OR REPLACE FUNCTION process_referral_bonus(
    p_referrer_id UUID,
    p_amount NUMERIC,
    p_referred_user_id UUID,
    p_deposit_amount NUMERIC,
    p_level INTEGER
)
RETURNS BOOLEAN AS $$
DECLARE
    v_current_balance NUMERIC;
    v_transaction_id UUID;
BEGIN
    -- Починаємо транзакцію
    -- Оновлюємо баланс реферера
    UPDATE users
    SET 
        balance = COALESCE(balance, 0) + p_amount,
        referral_earnings = COALESCE(referral_earnings, 0) + p_amount
    WHERE id = p_referrer_id
    RETURNING balance INTO v_current_balance;
    
    IF NOT FOUND THEN
        RETURN FALSE;
    END IF;
    
    -- Створюємо транзакцію
    INSERT INTO transactions (
        user_id,
        type,
        amount,
        balance_before,
        balance_after,
        description,
        metadata
    ) VALUES (
        p_referrer_id,
        'referral_bonus',
        p_amount,
        v_current_balance - p_amount,
        v_current_balance,
        CASE 
            WHEN p_level = 1 THEN 'Referral bonus (Level 1)'
            ELSE 'Referral bonus (Level 2)'
        END,
        jsonb_build_object(
            'referred_user_id', p_referred_user_id,
            'deposit_amount', p_deposit_amount,
            'level', p_level
        )
    ) RETURNING id INTO v_transaction_id;
    
    -- Оновлюємо статистику реферала
    UPDATE referrals
    SET 
        total_deposits = COALESCE(total_deposits, 0) + p_deposit_amount,
        total_bonuses_generated = COALESCE(total_bonuses_generated, 0) + p_amount,
        last_deposit_at = NOW(),
        bonus_paid = TRUE
    WHERE referrer_id = p_referrer_id 
        AND referred_id = p_referred_user_id
        AND level = p_level;
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- Функція для отримання статистики по днях
CREATE OR REPLACE FUNCTION get_daily_statistics(
    start_date DATE,
    end_date DATE
)
RETURNS TABLE (
    date DATE,
    new_users INTEGER,
    new_orders INTEGER,
    completed_orders INTEGER,
    total_revenue NUMERIC,
    total_deposits NUMERIC,
    total_withdrawals NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    WITH date_series AS (
        SELECT generate_series(start_date, end_date, '1 day'::interval)::date AS date
    )
    SELECT 
        ds.date,
        COUNT(DISTINCT u.id) FILTER (WHERE u.created_at::date = ds.date)::INTEGER as new_users,
        COUNT(DISTINCT o.id) FILTER (WHERE o.created_at::date = ds.date)::INTEGER as new_orders,
        COUNT(DISTINCT o.id) FILTER (WHERE o.created_at::date = ds.date AND o.status = 'completed')::INTEGER as completed_orders,
        COALESCE(SUM(o.charge) FILTER (WHERE o.created_at::date = ds.date), 0)::NUMERIC as total_revenue,
        COALESCE(SUM(t.amount) FILTER (WHERE t.created_at::date = ds.date AND t.type = 'deposit'), 0)::NUMERIC as total_deposits,
        COALESCE(ABS(SUM(t.amount) FILTER (WHERE t.created_at::date = ds.date AND t.type = 'withdrawal')), 0)::NUMERIC as total_withdrawals
    FROM date_series ds
    LEFT JOIN users u ON u.created_at::date = ds.date
    LEFT JOIN orders o ON o.created_at::date = ds.date
    LEFT JOIN transactions t ON t.created_at::date = ds.date
    GROUP BY ds.date
    ORDER BY ds.date;
END;
$$ LANGUAGE plpgsql;

-- Індекси для оптимізації
CREATE INDEX IF NOT EXISTS idx_orders_user_status ON orders(user_id, status);
CREATE INDEX IF NOT EXISTS idx_orders_created_status ON orders(created_at, status);
CREATE INDEX IF NOT EXISTS idx_transactions_user_type ON transactions(user_id, type);
CREATE INDEX IF NOT EXISTS idx_transactions_created_type ON transactions(created_at, type);
CREATE INDEX IF NOT EXISTS idx_referrals_referrer_level ON referrals(referrer_id, level);
CREATE INDEX IF NOT EXISTS idx_users_referral_earnings ON users(referral_earnings) WHERE referral_earnings > 0;

### Очищення старих даних
```sql
-- Видалення старих сесій
DELETE FROM user_sessions WHERE expires_at < NOW() - INTERVAL '30 days';

-- Архівування старих транзакцій
INSERT INTO transactions_archive SELECT * FROM transactions 
WHERE created_at < NOW() - INTERVAL '1 year';

DELETE FROM transactions WHERE created_at < NOW() - INTERVAL '1 year';
```

### Оновлення статистики
```sql
-- Оновлення статистики для query planner
ANALYZE users;
ANALYZE orders;
ANALYZE transactions;
ANALYZE referrals;

-- Перегляд розміру таблиць
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;


```

📞 КОНТАКТИ ТА ПІДТРИМКА
-----------------------

- **Проект**: TeleBoost
- **Версія БД**: 1.0.0
- **Останнє оновлення**: 31.01.2025
- **Автор документації**: TeleBoost Team

---

**Ця документація є повною та точною відповідно до поточної реалізації проекту TeleBoost**