-- ====================================================================
-- 1. CREATE ENUMS & EXTENSIONS
-- ====================================================================
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TYPE transmission_type AS ENUM ('Manual', 'Automatic', 'Hybrid');
CREATE TYPE inventory_status AS ENUM ('IN_STOCK', 'IN_TRANSIT', 'SOLD');
CREATE TYPE contact_type AS ENUM ('Lead', 'Customer');
CREATE TYPE order_status AS ENUM ('Inquiry', 'Booked', 'Delivered');
CREATE TYPE payment_mode AS ENUM ('Bank transfer', 'Demand Draft', 'Credit Card', 'Debit Card');
CREATE TYPE agent_role AS ENUM ('Sales Agent', 'Manager');
CREATE TYPE chat_status AS ENUM ('BOT_ACTIVE', 'HUMAN_REQUESTED', 'HUMAN_ACTIVE', 'RESOLVED');
CREATE TYPE message_sender AS ENUM ('USER', 'BOT', 'AGENT');

-- ====================================================================
-- 2. CREATE TABLES
-- ====================================================================

CREATE TABLE car_models (
    model_id VARCHAR(50) PRIMARY KEY,
    make VARCHAR(50) NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    transmission transmission_type NOT NULL,
    year INTEGER NOT NULL,
    Ex_Showroom_price NUMERIC(10, 2) NOT NULL,
    brochere_url VARCHAR(255)
);

CREATE TABLE dealerships (
    dealer_id VARCHAR(50) PRIMARY KEY,
    dealer_name VARCHAR(100) NOT NULL,
    city VARCHAR(100) NOT NULL,
    coordinate GEOGRAPHY(POINT, 4326) 
);

CREATE TABLE inventory (
    vin VARCHAR(17) PRIMARY KEY,
    model_id VARCHAR(50) REFERENCES car_models(model_id),
    color VARCHAR(50) NOT NULL,
    status inventory_status DEFAULT 'IN_STOCK',
    dealer_id VARCHAR(50) REFERENCES dealerships(dealer_id),
    image_url VARCHAR(255)
);

CREATE TABLE contacts (
    contact_id VARCHAR(50) PRIMARY KEY,
    phone_number VARCHAR(20) UNIQUE NOT NULL,
    type contact_type DEFAULT 'Lead',
    name VARCHAR(100),
    address TEXT
);

CREATE TABLE orders (
    order_id VARCHAR(50) PRIMARY KEY,
    contact_id VARCHAR(50) REFERENCES contacts(contact_id),
    vin VARCHAR(17) REFERENCES inventory(vin) UNIQUE, 
    additonal_fees JSONB,
    On_Road_price NUMERIC(10, 2) NOT NULL,
    dealer_id VARCHAR(50) REFERENCES dealerships(dealer_id),
    status order_status DEFAULT 'Inquiry',
    payment_mode payment_mode
);

CREATE TABLE agents (
    agent_id VARCHAR(50) PRIMARY KEY,
    sso_provider VARCHAR(50),
    sso_user_id VARCHAR(100) UNIQUE,
    email VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    role agent_role DEFAULT 'Sales Agent',
    is_online BOOLEAN DEFAULT FALSE,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE chat_sessions (
    session_id VARCHAR(50) PRIMARY KEY,
    contact_id VARCHAR(50) REFERENCES contacts(contact_id),
    agent_id VARCHAR(50) REFERENCES agents(agent_id), 
    status chat_status DEFAULT 'BOT_ACTIVE',
    ai_summary TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE messages (
    message_id VARCHAR(50) PRIMARY KEY,
    session_id VARCHAR(50) REFERENCES chat_sessions(session_id),
    sender_type message_sender NOT NULL,
    sender_id VARCHAR(50), 
    message_text TEXT NOT NULL,
    media_url VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ====================================================================
-- 3. INSERT DUMMY DATA FOR AI TESTING
-- ====================================================================

-- Dealerships placed strategically around Chennai
INSERT INTO dealerships (dealer_id, dealer_name, city, coordinate) VALUES
('dlr_che_01', 'Downtown Toyota', 'Chennai', ST_GeogFromText('SRID=4326;POINT(80.2707 13.0827)')),
('dlr_che_02', 'OMR Toyota', 'Chennai', ST_GeogFromText('SRID=4326;POINT(80.2280 12.9000)'));

-- 10 Requested Toyota Models (Pricing closely matches Indian Ex-Showroom estimates in INR)
INSERT INTO car_models (model_id, make, model_name, transmission, year, Ex_Showroom_price, brochere_url) VALUES
('mod_toy_lc300', 'Toyota', 'Land Cruiser 300', 'Automatic', 2026, 21000000.00, 'Toyota/LandCruiser/2026_brochure.pdf'),
('mod_toy_ebella', 'Toyota', 'Urban Cruiser Ebella', 'Automatic', 2026, 1500000.00, 'Toyota/UrbanCruiserEbella/2026_brochure.pdf'),
('mod_toy_taisor', 'Toyota', 'Urban Cruiser Taisor', 'Manual', 2024, 850000.00, 'Toyota/UrbanCruiserTaisor/2024_brochure.pdf'),
('mod_toy_hyryder', 'Toyota', 'Urban Cruiser Hyryder', 'Hybrid', 2026, 1650000.00, 'Toyota/UrbanCruiserHyryder/2026_brochure.pdf'),
('mod_toy_yaris', 'Toyota', 'Yaris Sedan', 'Manual', 2021, 1100000.00, 'Toyota/Yaris/2021_brochure.pdf'),
('mod_toy_vellfire', 'Toyota', 'Vellfire', 'Hybrid', 2026, 12200000.00, 'Toyota/Vellfire/2026_brochure.pdf'),
('mod_toy_rumion', 'Toyota', 'Rumion', 'Automatic', 2026, 1150000.00, 'Toyota/Rumion/2026_brochure.pdf'),
('mod_toy_camry', 'Toyota', 'Camry', 'Hybrid', 2026, 4650000.00, 'Toyota/Camry/2026_brochure.pdf'),
('mod_toy_corolla', 'Toyota', 'Corolla Cross', 'Hybrid', 2025, 3500000.00, 'Toyota/CorollaCross/2025_brochure.pdf'),
('mod_toy_fortuner', 'Toyota', 'Fortuner', 'Automatic', 2026, 3850000.00, 'Toyota/Fortuner/2026_brochure.pdf');

-- 22 Physical Inventory Units
INSERT INTO inventory (vin, model_id, color, status, dealer_id, image_url) VALUES
-- Land Cruiser 300
('JTM11111111111111', 'mod_toy_lc300', 'Precious White Pearl', 'IN_STOCK', 'dlr_che_01', 'Toyota/LandCruiser/white.jpg'),
('JTM11111111111112', 'mod_toy_lc300', 'Attitude Black', 'IN_TRANSIT', 'dlr_che_02', 'Toyota/LandCruiser/black.jpg'),
-- Ebella
('MBJ22222222222221', 'mod_toy_ebella', 'Iconic Silver', 'IN_STOCK', 'dlr_che_02', 'Toyota/UrbanCruiserEbella/silver.jpg'),
('MBJ22222222222222', 'mod_toy_ebella', 'Sport Red', 'IN_STOCK', 'dlr_che_02', 'Toyota/UrbanCruiserEbella/red.jpg'),
('MBJ22222222222223', 'mod_toy_ebella', 'Midnight Black', 'SOLD', 'dlr_che_01', 'Toyota/UrbanCruiserEbella/black.jpg'),
-- Taisor
('MBJ33333333333331', 'mod_toy_taisor', 'Lucent Orange', 'IN_STOCK', 'dlr_che_01', 'Toyota/UrbanCruiserTaisor/orange.jpg'),
('MBJ33333333333332', 'mod_toy_taisor', 'Cafe White', 'IN_STOCK', 'dlr_che_02', 'Toyota/UrbanCruiserTaisor/white.jpg'),
-- Hyryder
('MBJ44444444444441', 'mod_toy_hyryder', 'Speedy Blue', 'IN_STOCK', 'dlr_che_01', 'Toyota/UrbanCruiserHyryder/blue.jpg'),
('MBJ44444444444442', 'mod_toy_hyryder', 'Enticing Silver', 'IN_TRANSIT', 'dlr_che_02', 'Toyota/UrbanCruiserHyryder/silver.jpg'),
('MBJ44444444444443', 'mod_toy_hyryder', 'Cafe White', 'IN_STOCK', 'dlr_che_01', 'Toyota/UrbanCruiserHyryder/white.jpg'),
-- Yaris (Used/Older Stock)
('MBJ55555555555551', 'mod_toy_yaris', 'Phantom Brown', 'IN_STOCK', 'dlr_che_02', 'Toyota/Yaris/brown.jpg'),
-- Vellfire
('JTM66666666666661', 'mod_toy_vellfire', 'Burning Black', 'IN_STOCK', 'dlr_che_01', 'Toyota/Vellfire/black.jpg'),
('JTM66666666666662', 'mod_toy_vellfire', 'Platinum White Pearl', 'IN_TRANSIT', 'dlr_che_02', 'Toyota/Vellfire/white.jpg'),
-- Rumion
('MBJ77777777777771', 'mod_toy_rumion', 'Spunky Blue', 'IN_STOCK', 'dlr_che_02', 'Toyota/Rumion/blue.jpg'),
('MBJ77777777777772', 'mod_toy_rumion', 'Rustic Brown', 'SOLD', 'dlr_che_01', 'Toyota/Rumion/brown.jpg'),
-- Camry
('JTM88888888888881', 'mod_toy_camry', 'Attitude Black', 'IN_STOCK', 'dlr_che_01', 'Toyota/Camry/black.jpg'),
('JTM88888888888882', 'mod_toy_camry', 'Metal Stream Metallic', 'IN_STOCK', 'dlr_che_02', 'Toyota/Camry/silver.jpg'),
('JTM88888888888883', 'mod_toy_camry', 'Platinum White Pearl', 'IN_TRANSIT', 'dlr_che_01', 'Toyota/Camry/white.jpg'),
-- Corolla Cross
('JTM99999999999991', 'mod_toy_corolla', 'Celestite Gray', 'IN_TRANSIT', 'dlr_che_02', 'Toyota/CorollaCross/gray.jpg'),
('JTM99999999999992', 'mod_toy_corolla', 'Nebula Blue', 'IN_STOCK', 'dlr_che_01', 'Toyota/CorollaCross/blue.jpg'),
-- Fortuner
('MBJ00000000000001', 'mod_toy_fortuner', 'Phantom Brown', 'IN_STOCK', 'dlr_che_02', 'Toyota/Fortuner/brown.jpg'),
('MBJ00000000000002', 'mod_toy_fortuner', 'Super White', 'IN_STOCK', 'dlr_che_01', 'Toyota/Fortuner/white.jpg');

-- Sales Agent
INSERT INTO agents (agent_id, email, name, role) VALUES
('agt_001', 'vikram.singh@omrtoyota.in', 'Vikram Singh', 'Sales Agent');