-- Cardinal Phase 1 — data-tier schema + seed (MariaDB/MySQL).
-- Copied from sql-injection/webapp/db/init.sql, with the app DB user added:
-- Kathara bypasses the mariadb image entrypoint, so the MYSQL_USER/PASSWORD it
-- would normally create must be created here instead.
--
-- Passwords are stored in plaintext on purpose: this is a vulnerable testbed,
-- and the login SQLi scenario compares a concatenated vs parameterized query.

CREATE DATABASE IF NOT EXISTS portal CHARACTER SET utf8mb4;

-- Application DB account used by the webapp (host is unrestricted for the lab).
CREATE USER IF NOT EXISTS 'portal'@'%' IDENTIFIED BY 'portal';
GRANT ALL PRIVILEGES ON portal.* TO 'portal'@'%';
FLUSH PRIVILEGES;

USE portal;

CREATE TABLE IF NOT EXISTS users (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  username      VARCHAR(64) UNIQUE NOT NULL,
  password      VARCHAR(128) NOT NULL,
  display_name  VARCHAR(128),
  title         VARCHAR(128),
  department    VARCHAR(64),
  bio           TEXT,
  status        VARCHAR(255),
  homepage      VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS directory (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  name        VARCHAR(128) NOT NULL,
  title       VARCHAR(128),
  department  VARCHAR(64),
  email       VARCHAR(128),
  phone       VARCHAR(32),
  location    VARCHAR(64)
);

CREATE TABLE IF NOT EXISTS comments (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  record_id  INT NOT NULL,
  author     VARCHAR(64),
  body       TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO users (username, password, display_name, title, department, bio, status, homepage) VALUES
  ('alice', 'alicepw', 'Alice Nguyen', 'Directory Administrator', 'IT', 'Maintains the staff directory and access policy.', 'available', 'https://intranet.local/~alice'),
  ('bob',   'bobpw',   'Bob Carter',   'Facilities Coordinator',  'Facilities', 'Front-desk and building operations.', 'in a meeting', 'https://intranet.local/~bob'),
  ('carol', 'carolpw', 'Carol Diaz',   'People Operations Lead',  'HR', 'Onboarding, benefits, and org policy.', 'out of office until Mon', 'https://intranet.local/~carol')
ON DUPLICATE KEY UPDATE username = username;

INSERT INTO directory (name, title, department, email, phone, location) VALUES
  ('Alice Nguyen',  'Directory Administrator', 'IT',          'alice@corp.local',  'x2210', 'HQ · 2F'),
  ('Bob Carter',    'Facilities Coordinator',  'Facilities',  'bob@corp.local',    'x2011', 'HQ · Lobby'),
  ('Carol Diaz',    'People Operations Lead',  'HR',          'carol@corp.local',  'x2450', 'HQ · 3F'),
  ('David Osei',    'Senior Engineer',         'Engineering', 'david@corp.local',  'x3120', 'HQ · 4F'),
  ('Erin Walsh',    'Financial Analyst',       'Finance',     'erin@corp.local',   'x2740', 'HQ · 3F'),
  ('Frank Mensah',  'Support Specialist',      'IT',          'frank@corp.local',  'x2233', 'Remote'),
  ('Grace Park',    'Product Manager',         'Product',     'grace@corp.local',  'x3305', 'HQ · 4F'),
  ('Henry Adjei',   'Account Executive',       'Sales',       'henry@corp.local',  'x2802', 'Field'),
  ('Ivy Lindqvist', 'UX Designer',             'Product',     'ivy@corp.local',    'x3311', 'HQ · 4F'),
  ('Jamal Rahman',  'Security Engineer',       'Engineering', 'jamal@corp.local',  'x3140', 'HQ · 4F'),
  ('Kofi Boateng',  'Data Analyst',            'Finance',     'kofi@corp.local',   'x2755', 'HQ · 3F'),
  ('Lena Fischer',  'Recruiter',               'HR',          'lena@corp.local',   'x2460', 'HQ · 3F'),
  ('Maya Okonkwo',  'DevOps Engineer',         'Engineering', 'maya@corp.local',   'x3155', 'HQ · 4F'),
  ('Noah Bergstrom', 'Marketing Manager',      'Marketing',   'noah@corp.local',   'x2905', 'HQ · 2F'),
  ('Priya Sharma',  'Legal Counsel',           'Legal',       'priya@corp.local',  'x2600', 'HQ · 3F'),
  ('Omar Haddad',   'Sales Engineer',          'Sales',       'omar@corp.local',   'x2820', 'Field'),
  ('Sofia Rossi',   'QA Engineer',             'Engineering', 'sofia@corp.local',  'x3160', 'Remote');

INSERT INTO comments (record_id, author, body) VALUES
  (1, 'bob',   'Alice sorted out my directory access same day. Great help.'),
  (1, 'carol', 'Approved the new directory layout — looks much cleaner.'),
  (4, 'grace', 'David led the search-service migration. Solid work.'),
  (7, 'ivy',   'Grace ran a really tight roadmap review this quarter.');
