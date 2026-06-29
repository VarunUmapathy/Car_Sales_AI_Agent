CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TYPE transmission_type AS ENUM ('Manual', 'Automatic', 'Hybrid');
CREATE TYPE inventory_status AS ENUM ('IN_STOCK', 'IN_TRANSIT', 'SOLD');
CREATE TYPE contact_type AS ENUM ('Lead', 'Customer');
CREATE TYPE order_status AS ENUM ('Inquiry', 'Booked', 'Delivered');
CREATE TYPE payment_mode AS ENUM ('Bank transfer', 'Demand Draft', 'Credit Card', 'Debit Card');
CREATE TYPE agent_role AS ENUM ('Sales Agent', 'Manager');
CREATE TYPE chat_status AS ENUM ('BOT_ACTIVE', 'HUMAN_REQUESTED', 'HUMAN_ACTIVE', 'RESOLVED');
CREATE TYPE message_sender AS ENUM ('USER', 'BOT', 'AGENT');

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

INSERT INTO dealerships (dealer_id, dealer_name, city, coordinate) VALUES
('dlr_001', 'Downtown Honda', 'New York', ST_GeogFromText('SRID=4326;POINT(-74.0060 40.7128)')),
('dlr_002', 'Westside Toyota', 'Los Angeles', ST_GeogFromText('SRID=4326;POINT(-118.2437 34.0522)'));

INSERT INTO car_models (model_id, make, model_name, transmission, year, Ex_Showroom_price, brochere_url) VALUES
('mod_honda_01', 'Honda', 'Civic', 'Automatic', 2024, 24000.00),
('mod_toyota_01', 'Toyota', 'RAV4', 'Hybrid', 2024, 32000.00);

INSERT INTO inventory (vin, model_id, color, status, dealer_id, image_url) VALUES
('VIN1HGCM823456781', 'mod_honda_01', 'Blue', 'IN_STOCK', 'dlr_001'),
('VIN1HGCM823456782', 'mod_honda_01', 'Red', 'IN_STOCK', 'dlr_001'),
('VINJTMBVD34567891', 'mod_toyota_01', 'White', 'IN_TRANSIT', 'dlr_002');

INSERT INTO agents (agent_id, email, name, role) VALUES
('agt_001', 'sarah@dealership.com', 'Sarah Connor', 'Sales Agent');