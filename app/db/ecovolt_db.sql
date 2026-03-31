-- =========================
-- CRIAR BASE DE DADOS
-- =========================
CREATE DATABASE IF NOT EXISTS countlight_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE countlight_db;

-- =========================
-- ROLES
-- =========================
CREATE TABLE roles (
    id_role INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    description VARCHAR(255)
) ENGINE=InnoDB;

INSERT INTO roles (name, description) VALUES
('user', 'Utilizador normal'),
('admin', 'Administrador do sistema');

-- =========================
-- USERS
-- =========================
CREATE TABLE users (
    id_user INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    id_role INT NOT NULL DEFAULT 1,
    refresh_token VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_users_roles
        FOREIGN KEY (id_role) REFERENCES roles(id_role)
) ENGINE=InnoDB;

-- =========================
-- USER PROFILES
-- =========================
CREATE TABLE user_profiles (
    id_user_profile INT AUTO_INCREMENT PRIMARY KEY,
    id_user INT NOT NULL UNIQUE,
    description TEXT,
    photo_url VARCHAR(255),
    CONSTRAINT fk_profiles_users
        FOREIGN KEY (id_user) REFERENCES users(id_user) ON DELETE CASCADE
) ENGINE=InnoDB;

-- =========================
-- PLANS
-- =========================
CREATE TABLE plans (
    id_plan INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    price_monthly DECIMAL(6,2) NOT NULL,
    max_houses INT NOT NULL,
    max_devices INT NOT NULL,
    history_days INT NOT NULL,
    features_json JSON
) ENGINE=InnoDB;

INSERT INTO plans (name, price_monthly, max_houses, max_devices, history_days) VALUES
('Free', 0.00, 1, 3, 30),
('Base', 6.99, 2, 5, 90),
('Avançado', 12.99, 5, 10, 365);

-- =========================
-- SUBSCRIPTIONS
-- =========================
CREATE TABLE subscriptions (
    id_subscription INT AUTO_INCREMENT PRIMARY KEY,
    id_user INT NOT NULL,
    id_plan INT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE,
    is_active BOOLEAN DEFAULT TRUE,
    CONSTRAINT fk_subscriptions_users
        FOREIGN KEY (id_user) REFERENCES users(id_user) ON DELETE CASCADE,
    CONSTRAINT fk_subscriptions_plans
        FOREIGN KEY (id_plan) REFERENCES plans(id_plan)
) ENGINE=InnoDB;

-- =========================
-- HOUSES
-- =========================
CREATE TABLE houses (
    id_house INT AUTO_INCREMENT PRIMARY KEY,
    id_user INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    address VARCHAR(255),
    house_type ENUM('apartamento', 'moradia') NOT NULL,
    adults INT DEFAULT 0,
    children INT DEFAULT 0,
    occupancy_type ENUM('permanente', 'parcial', 'ferias') NOT NULL,
    provider VARCHAR(100),
    tariff VARCHAR(100),
    contract_power DECIMAL(5,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_houses_users
        FOREIGN KEY (id_user) REFERENCES users(id_user) ON DELETE CASCADE
) ENGINE=InnoDB;

-- =========================
-- ROOMS
-- =========================
CREATE TABLE rooms (
    id_room INT AUTO_INCREMENT PRIMARY KEY,
    id_house INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_rooms_houses
        FOREIGN KEY (id_house) REFERENCES houses(id_house) ON DELETE CASCADE
) ENGINE=InnoDB;

-- =========================
-- DEVICES (Shelly)
-- =========================
CREATE TABLE devices (
    id_device INT AUTO_INCREMENT PRIMARY KEY,
    id_room INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    shelly_id VARCHAR(100) NOT NULL UNIQUE,
    device_type VARCHAR(100),
    energy_class ENUM('A','B','C','D','E','F','G'),
    is_active BOOLEAN DEFAULT TRUE,
    CONSTRAINT fk_devices_rooms
        FOREIGN KEY (id_room) REFERENCES rooms(id_room) ON DELETE CASCADE
) ENGINE=InnoDB;

-- =========================
-- ENERGY READINGS
-- =========================
CREATE TABLE energy_readings (
    id_energy_reading BIGINT AUTO_INCREMENT PRIMARY KEY,
    id_device INT NOT NULL,
    power_w DECIMAL(7,2) NOT NULL,
    energy_kwh DECIMAL(10,5) NOT NULL,
    recorded_at DATETIME NOT NULL,
    CONSTRAINT fk_readings_devices
        FOREIGN KEY (id_device) REFERENCES devices(id_device) ON DELETE CASCADE,
    INDEX idx_energy_readings_time (recorded_at)
) ENGINE=InnoDB;

-- =========================
-- ALERTS
-- =========================
CREATE TABLE alerts (
    id_alert INT AUTO_INCREMENT PRIMARY KEY,
    id_house INT NOT NULL,
    id_device INT,
    title VARCHAR(150) NOT NULL,
    description TEXT,
    power_w DECIMAL(7,2),
    triggered_at DATETIME NOT NULL,
    CONSTRAINT fk_alerts_houses
        FOREIGN KEY (id_house) REFERENCES houses(id_house) ON DELETE CASCADE,
    CONSTRAINT fk_alerts_devices
        FOREIGN KEY (id_device) REFERENCES devices(id_device) ON DELETE SET NULL
) ENGINE=InnoDB;

-- =========================
-- RECOMMENDATIONS
-- =========================
CREATE TABLE recommendations (
    id_recommendation INT AUTO_INCREMENT PRIMARY KEY,
    id_house INT NOT NULL,
    type VARCHAR(100),
    title VARCHAR(150) NOT NULL,
    description TEXT,
    estimated_savings_monthly DECIMAL(7,2),
    estimated_savings_yearly DECIMAL(7,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    CONSTRAINT fk_recommendations_houses
        FOREIGN KEY (id_house) REFERENCES houses(id_house) ON DELETE CASCADE
) ENGINE=InnoDB;

-- =========================
-- ACHIEVEMENTS
-- =========================
CREATE TABLE achievements (
    id_achievement INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(150) NOT NULL,
    description TEXT,
    target_value DECIMAL(10,2),
    metric VARCHAR(50),
    is_custom BOOLEAN DEFAULT FALSE
) ENGINE=InnoDB;

CREATE TABLE user_achievements (
    id_user_achievement INT AUTO_INCREMENT PRIMARY KEY,
    id_user INT NOT NULL,
    id_achievement INT NOT NULL,
    status ENUM('completed', 'ongoing', 'failed') DEFAULT 'ongoing',
    progress DECIMAL(10,2) DEFAULT 0,
    completed_at DATETIME,
    CONSTRAINT fk_user_achievements_users
        FOREIGN KEY (id_user) REFERENCES users(id_user) ON DELETE CASCADE,
    CONSTRAINT fk_user_achievements_achievements
        FOREIGN KEY (id_achievement) REFERENCES achievements(id_achievement) ON DELETE CASCADE
) ENGINE=InnoDB;

-- =========================
-- DAILY INSIGHTS
-- =========================
CREATE TABLE daily_insights (
    id_daily_insight INT AUTO_INCREMENT PRIMARY KEY,
    id_house INT NOT NULL,
    date DATE NOT NULL,
    text TEXT NOT NULL,
    CONSTRAINT fk_insights_houses
        FOREIGN KEY (id_house) REFERENCES houses(id_house) ON DELETE CASCADE
) ENGINE=InnoDB;

-- =========================
-- ENERGY PRICES
-- =========================
CREATE TABLE energy_prices (
    id_energy_price INT AUTO_INCREMENT PRIMARY KEY,
    provider VARCHAR(100),
    tariff VARCHAR(100),
    price_kwh DECIMAL(6,4),
    start_date DATE,
    end_date DATE
) ENGINE=InnoDB;
