# Pencil Production Line Project Report Outline

## Task 1: Introduction

The selected product for this project is a pencil. A pencil is suitable for a production-line simulation because it consists of several clearly identifiable components that must be assembled in a fixed sequence. The main components used in this project are the graphite core, wooden body, eraser, and eraser holder. These components satisfy the requirement of a production line with at least four components or stages.

The proposed production line simulates an automated pencil assembly process. First, the graphite core is inserted. Second, the wooden body is assembled around the core. Third, the eraser is attached to the back end of the pencil. Fourth, the eraser holder, also known as the ferrule, is attached to secure the eraser. Finally, the assembled pencil passes through a quality-control station. The quality-control station checks whether all components are present and whether the pencil dimensions are within tolerance.

## Task 2: Program Development

The program is divided into backend logic, frontend HMI, database communication, and dashboard visualization.

The backend is written in Python. It defines the pencil object, the machine state, the production stations, the counters, and the defect-detection rules. The backend marks a pencil as defective when a graphite core is missing or broken, the wooden body is cracked, the eraser is missing or misaligned, the eraser holder is loose, or the final length and diameter are outside the tolerance range. Critical conditions such as a jam or high machine temperature create a fault state.

The frontend is implemented as a Tkinter HMI. It includes Start, Stop, Reset, and Ack Fault buttons. The interface displays the current machine state, the active station, the product number, total produced pencils, good pencils, defective pencils, temperature, and the last defect reason. The visual layout shows five station blocks connected as a production line. The active station changes color during production, and faulted stations are displayed as an alarm condition.

The database layer uses InfluxDB. The Python program sends production data to the measurement named `pencil_line`. The stored parameters include machine state, produced count, good count, defective count, current station index, current product ID, and machine temperature.

The dashboard layer uses Grafana. Grafana reads the values from InfluxDB and displays them in time-series panels. The dashboard can show produced pencils, rejected pencils, machine state, and machine temperature. These parameters allow the operator to monitor the behavior of the simulated production line.

Optional quality-control functionality is included because the simulation does not simply count parts; it also decides whether a pencil is accepted or rejected. This makes the line closer to a real automated assembly system.

## Task 3: Tools Used

Git and GitHub were used for version control and project hosting. Git was used to track changes in the Python code, documentation, Docker configuration, and dashboard files. GitHub was used to host the repository and can also be used to publish the project website through GitHub Pages.

Docker was used to run the database and dashboard services. The Docker Compose file starts InfluxDB and Grafana with the required configuration. This makes the system easier to run because the database and dashboard do not need to be installed manually.

Python was used for the production-line simulation and HMI. Tkinter was selected for the frontend because it is included with most Python installations and is suitable for a simple machine interface. The InfluxDB Python client was used to send simulated production data to the database.

AI tools may be used to support code generation, debugging, and documentation. Any AI-generated code should be checked manually, tested, corrected, and documented in the appendix of the report.

## Task 4: Conclusion

The developed system demonstrates a complete simulated pencil production line with backend logic, HMI operation, database storage, and dashboard visualization. The main strength of the implementation is that it combines production-line behavior with realistic machine states and defect reasons. The operator can start, stop, reset, and acknowledge faults from the HMI, while production data is stored for later analysis in Grafana.

A weakness of the implementation is that the defects are simulated using random probabilities rather than real sensor inputs. Therefore, the system represents the logic of an automated production line but not the complete physical behavior of an actual pencil factory. Another limitation is that the HMI is simple and designed mainly for demonstration purposes.

Further development could include real sensor data, PLC communication, SCADA integration, maintenance scheduling, operator login, alarm history, and more detailed quality-control statistics. In a real industrial system, requirements such as safety, reliability, cybersecurity, maintainability, calibration, and traceability would become important.
