CountLight

Plataforma web para monitorização e gestão inteligente do consumo energético doméstico, desenvolvida no âmbito do Trabalho Final de Curso (TFC) em Engenharia Informática.

---

Descrição

O CountLight é uma aplicação web que permite aos utilizadores acompanhar, analisar e otimizar o consumo de energia em tempo real, através da integração com dispositivos IoT.

A solução disponibiliza dashboards interativos, históricos de consumo, alertas automáticos e simulação de custos, promovendo uma gestão energética mais eficiente e informada.

---

Acesso

- Aplicação: https://countlight.duckdns.org/
- Repositório: https://github.com/Nogueira7/CountLight

---

Demonstração
- (Adicionar aqui o link do vídeo)

---

Funcionalidades

- Autenticação de utilizadores (JWT)
- Monitorização de consumo em tempo real
- Visualização de dados históricos
- Dashboards interativos
- Alertas automáticos de consumo
- Simulação de custos energéticos
- Gestão de dispositivos e divisões

---

Arquitetura

O sistema segue uma arquitetura cliente-servidor em camadas, composta por:

- Frontend - Interface web para o utilizador  
- Backend - API REST responsável pela lógica de negócio  
- Base de Dados - Armazenamento persistente  
- Data Ingestion - Recolha de dados via MQTT  

Conforme descrito no relatório, o backend está organizado em:

- Rotas (endpoints)
- Serviços
- Repositórios
- Modelos

---

Tecnologias Utilizadas

Backend
- Python
- FastAPI
- Uvicorn
- MySQL
- JWT (autenticação)

Frontend
- HTML
- CSS
- JavaScript
- Chart.js

Infraestrutura
- Docker
- Nginx
- VPS (Ubuntu)
- MQTT (Mosquitto)
- DuckDNS

---

Segurança

- Autenticação com JWT (access + refresh tokens)
- Passwords com hashing (bcrypt)
- Cookies HTTPOnly e Secure
- Proteção contra ataques XSS
- Validação de dados em todas as camadas

---

Instalação (Desenvolvimento)

```bash
Clonar repositório
git clone https://github.com/Nogueira7/CountLight.git

Entrar na pasta
cd CountLight

Executar com Docker
docker-compose up --build
