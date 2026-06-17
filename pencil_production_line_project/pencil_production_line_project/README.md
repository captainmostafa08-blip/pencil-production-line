# Pencil Production Line Simulation

This project simulates an automated production line for assembling pencils. It follows the required assignment structure: backend logic in Python, frontend HMI with buttons, InfluxDB database, and Grafana dashboard.

## Product and stages

The selected product is a pencil. The simulated production line has five stations:

1. Graphite core insertion
2. Wooden body assembly
3. Eraser attachment
4. Eraser holder/ferrule attachment
5. Final quality control

A product is marked as defective when one of the following occurs:

- Missing or broken graphite core
- Cracked or incomplete wooden body
- Missing or misaligned eraser
- Loose or missing eraser holder
- Pencil length or diameter outside tolerance
- Assembly jam or high temperature fault

## How to run the project

### 1. Start InfluxDB and Grafana

```bash
docker compose up -d
```

InfluxDB: http://localhost:8086

Grafana: http://localhost:3000

Grafana login:

- Username: `admin`
- Password: `admin`

InfluxDB is initialized with:

- Organization: `srh`
- Bucket: `pencil_line`
- Token: `pencil-token`

### 2. Install Python requirements

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Run the HMI

```bash
python app.py
```

The HMI has four operator buttons:

- Start: starts the production process
- Stop: stops the line
- Reset: resets counters and status
- Ack Fault: acknowledges a fault and returns the line to stopped state

## Grafana dashboard

The dashboard is automatically provisioned when Docker starts. It displays:

- Produced pencils
- Good pencils
- Defective pencils
- Machine temperature
- Machine state value: 0 = stopped, 1 = running, 2 = faulted
- Current station index

## Project structure

```text
pencil_production_line_project/
├── app.py
├── requirements.txt
├── docker-compose.yml
├── README.md
├── docs/
│   └── report_outline.md
└── grafana/
    ├── provisioning/
    │   ├── datasources/influxdb.yml
    │   └── dashboards/dashboard.yml
    └── dashboards/pencil_line_dashboard.json
```

## AI use statement

If AI tools were used during development, document the prompts, the generated output, the corrections made, and the benefits of using the tool in the appendix of the final report.
