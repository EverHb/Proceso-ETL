CREATE DATABASE foods_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE foods_db;

CREATE TABLE cuisine (
    id   INT PRIMARY KEY,
    name VARCHAR(50) NOT NULL
);
 
INSERT INTO cuisine (id, name) VALUES
    (1, 'Other'),
    (2, 'Chinese'),
    (3, 'Italian'),
    (4, 'Indian');
 
CREATE TABLE category (
    id   INT PRIMARY KEY,
    name VARCHAR(50) NOT NULL
);
 
INSERT INTO category (id, name) VALUES
    (1, 'Main Course'),
    (2, 'Starter'),
    (3, 'Beverage'),
    (4, 'Dessert');
 
CREATE TABLE food_type (
    id   INT PRIMARY KEY,
    name VARCHAR(50) NOT NULL
);
 
INSERT INTO food_type (id, name) VALUES
    (1, 'Vegan'),
    (2, 'Non-Veg'),
    (3, 'Jain'),
    (4, 'Veg');
 
CREATE TABLE spice_level (
    id   INT PRIMARY KEY,
    name VARCHAR(50) NOT NULL
);
 
INSERT INTO spice_level (id, name) VALUES
    (1, 'Mild'),
    (2, 'Spicy'),
    (3, 'Medium');
 
CREATE TABLE tax_rate (
    id         INT PRIMARY KEY,
    percentage DECIMAL(5,2) NOT NULL
);
 
INSERT INTO tax_rate (id, percentage) VALUES
    (1, 0),
    (2, 5),
    (3, 12),
    (4, 18);
 
-- ------------------------------------------------------------
-- Tabla principal donde el ETL insertará los datos procesados.
-- NOTA: pandas.to_sql con if_exists="replace" ELIMINA y RECREA
-- esta tabla automáticamente, así que no es estrictamente
-- necesario crearla a mano. Pero si quieres controlar tipos de
-- dato exactos y las llaves foráneas desde el inicio, créala así
-- y cambia el script Python a if_exists="append" en vez de
-- "replace" (para no perder las FKs cada vez que corres el ETL).
-- ------------------------------------------------------------
 
CREATE TABLE etl_platos_procesados (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    restaurant_id   VARCHAR(50) NOT NULL,
    dish_name       VARCHAR(255) NOT NULL,
    description     TEXT,
    price           DECIMAL(10,2) NOT NULL,
    image_url       VARCHAR(500),
    created_at      DATE,
    cuisine_id      INT NOT NULL,
    category_id     INT NOT NULL,
    food_type_id    INT NOT NULL,
    spice_level_id  INT NOT NULL,
    tax_rate_id     INT NOT NULL,
 
    CONSTRAINT fk_cuisine     FOREIGN KEY (cuisine_id)     REFERENCES cuisine(id),
    CONSTRAINT fk_category    FOREIGN KEY (category_id)    REFERENCES category(id),
    CONSTRAINT fk_food_type   FOREIGN KEY (food_type_id)   REFERENCES food_type(id),
    CONSTRAINT fk_spice_level FOREIGN KEY (spice_level_id) REFERENCES spice_level(id),
    CONSTRAINT fk_tax_rate    FOREIGN KEY (tax_rate_id)    REFERENCES tax_rate(id)
);