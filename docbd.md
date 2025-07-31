📊 ОНОВЛЕНА ДОКУМЕНТАЦІЯ БАЗИ ДАНИХ SUPABASE
1️⃣ Таблиця користувачів (users)
sql-- Створення таблиці users
CREATE TABLE users (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    telegram_id TEXT UNIQUE NOT NULL,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    language_code TEXT DEFAULT 'en',
    is_premium BOOLEAN DEFAULT false,
    is_admin BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    
    -- Баланс та статистика
    balance DECIMAL(15,2) DEFAULT 0.00,
    total_deposited DECIMAL(15,2) DEFAULT 0.00,
    total_withdrawn DECIMAL(15,2) DEFAULT 0.00,
    total_spent DECIMAL(15,2) DEFAULT 0.00,
    
    -- Реферальна система
    referral_code TEXT UNIQUE,
    referred_by UUID REFERENCES users(id),
    referral_earnings DECIMAL(15,2) DEFAULT 0.00,
    
    -- Дати
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_login TIMESTAMPTZ,
    
    -- Додаткові дані
    photo_url TEXT,
    settings JSONB DEFAULT '{}',
    
    -- Індекси
    CONSTRAINT positive_balance CHECK (balance >= 0)
);

-- Індекси для швидкого пошуку
CREATE INDEX idx_users_telegram_id ON users(telegram_id);
CREATE INDEX idx_users_referral_code ON users(referral_code);
CREATE INDEX idx_users_referred_by ON users(referred_by);
CREATE INDEX idx_users_created_at ON users(created_at DESC);
2️⃣ Таблиця сесій (user_sessions)
sql-- Таблиця для сесій користувачів
CREATE TABLE user_sessions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    access_token_jti TEXT NOT NULL,
    refresh_token_jti TEXT NOT NULL,
    ip_address TEXT,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    is_active BOOLEAN DEFAULT true,
    
    -- Індекси
    CONSTRAINT unique_access_jti UNIQUE(access_token_jti),
    CONSTRAINT unique_refresh_jti UNIQUE(refresh_token_jti)
);

CREATE INDEX idx_sessions_user_id ON user_sessions(user_id);
CREATE INDEX idx_sessions_expires_at ON user_sessions(expires_at);
CREATE INDEX idx_sessions_active ON user_sessions(is_active);
3️⃣ Таблиця транзакцій (transactions)
sql-- Таблиця транзакцій
CREATE TABLE transactions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type TEXT NOT NULL CHECK (type IN ('deposit', 'withdraw', 'order', 'refund', 'referral_bonus', 'cashback', 'admin_credit', 'admin_debit')),
    amount DECIMAL(15,2) NOT NULL,
    balance_before DECIMAL(15,2) NOT NULL,
    balance_after DECIMAL(15,2) NOT NULL,
    description TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_transactions_user_id ON transactions(user_id);
CREATE INDEX idx_transactions_type ON transactions(type);
CREATE INDEX idx_transactions_created_at ON transactions(created_at DESC);
4️⃣ Таблиця сервісів (services) - ОНОВЛЕНА
sql-- Таблиця сервісів Nakrutochka
CREATE TABLE services (
    id INTEGER PRIMARY KEY,  -- Nakrutochka service ID
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    category TEXT NOT NULL,
    rate DECIMAL(15,4) NOT NULL,
    min INTEGER NOT NULL,
    max INTEGER NOT NULL,
    dripfeed BOOLEAN DEFAULT false,
    refill BOOLEAN DEFAULT false,
    cancel BOOLEAN DEFAULT false,
    description TEXT,
    position INTEGER DEFAULT 999,
    tags TEXT[] DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    status TEXT DEFAULT 'active',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_services_category ON services(category);
CREATE INDEX idx_services_type ON services(type);
CREATE INDEX idx_services_active ON services(is_active);
CREATE INDEX idx_services_position ON services(position);
5️⃣ Таблиця замовлень (orders)
sql-- Таблиця замовлень
CREATE TABLE orders (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    nakrutochka_order_id TEXT UNIQUE,
    service_id INTEGER NOT NULL REFERENCES services(id),
    link TEXT NOT NULL,
    quantity INTEGER,
    comments TEXT,
    charge DECIMAL(15,2) NOT NULL,
    remains INTEGER DEFAULT 0,
    start_count INTEGER DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_created_at ON orders(created_at DESC);
CREATE INDEX idx_orders_nakrutochka_id ON orders(nakrutochka_order_id);
6️⃣ Таблиця платежів (payments)
sql-- Таблиця платежів
CREATE TABLE payments (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    payment_id TEXT UNIQUE NOT NULL,
    provider TEXT NOT NULL CHECK (provider IN ('cryptobot', 'nowpayments', 'monobank')),
    type TEXT NOT NULL CHECK (type IN ('deposit', 'withdraw')),
    amount DECIMAL(15,2) NOT NULL,
    currency TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'waiting',
    payment_url TEXT,
    expires_at TIMESTAMPTZ,
    paid_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_payments_user_id ON payments(user_id);
CREATE INDEX idx_payments_payment_id ON payments(payment_id);
CREATE INDEX idx_payments_status ON payments(status);
CREATE INDEX idx_payments_created_at ON payments(created_at DESC);
7️⃣ Таблиця рефералів (referrals) - НОВА
sql-- Таблиця рефералів
CREATE TABLE referrals (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    referrer_id UUID NOT NULL REFERENCES users(id),
    referred_id UUID NOT NULL REFERENCES users(id),
    bonus_paid BOOLEAN DEFAULT false,
    bonus_amount DECIMAL(15,2) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_referrals_referrer ON referrals(referrer_id);
CREATE INDEX idx_referrals_referred ON referrals(referred_id);
CREATE UNIQUE INDEX idx_referrals_unique ON referrals(referrer_id, referred_id);
8️⃣ Таблиця статистики бота (bot_stats) - НОВА
sql-- Таблиця статистики бота
CREATE TABLE bot_stats (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_count INTEGER DEFAULT 0,
    order_count INTEGER DEFAULT 0, 
    total_revenue DECIMAL(15,2) DEFAULT 0,
    date DATE UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_bot_stats_date ON bot_stats(date);
9️⃣ RPC функції для атомарних операцій
sql-- Функція для оновлення балансу (атомарна операція)
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

-- Функція для зменшення балансу
CREATE OR REPLACE FUNCTION decrement_balance(
    user_id UUID,
    amount DECIMAL
) RETURNS BOOLEAN AS $$
BEGIN
    RETURN increment_balance(user_id, -amount);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
🔟 Тригери для автоматичного оновлення updated_at
sql-- Функція для оновлення updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Тригери для таблиць
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_orders_updated_at BEFORE UPDATE ON orders
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_payments_updated_at BEFORE UPDATE ON payments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_services_updated_at BEFORE UPDATE ON services
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_bot_stats_updated_at BEFORE UPDATE ON bot_stats
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
📋 ЗМІНИ ВІДНОСНО ПОПЕРЕДНЬОЇ ВЕРСІЇ:
✅ Змінено в таблиці services:

id INTEGER PRIMARY KEY - тепер використовує Nakrutochka ID напряму
Видалено поле service_id - більше не потрібне
Додано нові поля:

refill BOOLEAN DEFAULT false
cancel BOOLEAN DEFAULT false
position INTEGER DEFAULT 999
tags TEXT[] DEFAULT '{}'
metadata JSONB DEFAULT '{}'
status TEXT DEFAULT 'active'



✅ Додано нові таблиці:

referrals - для відстеження реферальних зв'язків
bot_stats - для збору статистики бота

✅ Додано індекси:

idx_services_position - для сортування сервісів
idx_referrals_unique - унікальний індекс для запобігання дублікатів

🎯 ВАЖЛИВІ ПРИМІТКИ:

Таблиця services тепер використовує Nakrutochka service ID як primary key
Реферальна система тепер має окрему таблицю для кращого трекінгу
Статистика бота збирається по днях для аналітики
Всі таблиці мають автоматичне оновлення updated_at через тригери
Додано більше індексів для оптимізації запитів