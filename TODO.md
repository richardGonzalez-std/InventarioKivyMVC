# TODO - SIAM Implementation Roadmap

**Sistema de Inventario Automático de Materiales y Equipos de Cocina (SIAM)**
Comedor de Empleados - CORPOELEC

---

## Documentation Reference

| ID | Document | Description | Version |
|----|----------|-------------|---------|
| DAR-SIAM | DAR_TAU.docx | Descubrimiento y Análisis de Requisitos | 0.1 |
| MDN-SIAM | MDN TAU.docx | Modelo del Negocio | 0.1 |
| MCUN-SIAM | MCUN TAU.docx | Modelo de Casos de Uso del Negocio | 0.1 |
| ERS-SIAM | ERS_TAU.pdf | Especificación de Requisitos del Software | 1.0 |
| ECU-SIAM | ECU_TAU.pdf/docx | Especificación de Casos de Uso | 0.1 |
| DAS-SIAM | DAS_TAU.pdf | Diseño Arquitectónico del Software | 0.0 |
| PPR-SIAM | PPR TAU.docx | Plan de Pruebas del Software | 1.0 |
| ECP-SIAM | ECPCU1-TAU.docx.pdf | Especificación de Casos de Pruebas | 1.0 |

---

## Business Objectives (from MDN)

- [ ] Reduce monthly item shortage rate to less than 1%
- [ ] Cut average entry/exit registration time by 50%
- [ ] Generate automatic restock alerts at critical stock levels
- [ ] Maintain transaction history for at least 5 years with full traceability
- [ ] Implement inventory rotation and service level indicators

---

## Phase 1: Database & Foundation

### 1.1 Database Implementation (SIAM-RC-03)
- [ ] Implement PostgreSQL 15 database connection
- [ ] Create database schema based on DAS entities:
  - [ ] `Material` (idMaterial, nombre, descripcion, cantidadActual, unidadMedida, stockMinimo)
  - [ ] `Usuario` (idUsuario, nombreUsuario, contrasena, rol)
  - [ ] `Movimiento` (idMovimiento, idMaterial, tipoMovimiento, cantidad, fecha, idUsuario)
  - [ ] `Categoria` (for material categories)
  - [ ] `Alerta_Reabastecimiento` (stock alerts)
  - [ ] `Orden_Mantenimiento` (maintenance orders)
  - [ ] `Transaccion_Inventario` (audit trail - RE-06)
- [ ] Replace `DummyDatabase` with PostgreSQL implementation
- [ ] Database migration scripts
- [ ] 5-year data retention policy implementation (RE-02)

### 1.2 Authentication System (SIAM-RC-04)
- [ ] Active Directory integration (corporate auth)
- [ ] Login screen with credentials
- [ ] Role-based access control:
  - [ ] Encargado de Almacén (warehouse operations)
  - [ ] Empleado del Comedor (queries, report shortages)
  - [ ] Gerente del Comedor (supervision, approvals)
  - [ ] Administrador (full access)
- [ ] Session management with user context
- [ ] User traceability logging (LG04, RE-06)

---

## Phase 2: Business Use Cases (CUN-001 to CUN-006)

### 2.1 CUN-001 / CU-001: Registrar Entrada de Material
**Actor:** Encargado de Almacén

- [ ] Material entry form screen with fields:
  - [ ] Código/ID Material (alphanumeric, max 20 chars) - DT02
  - [ ] Nombre del Material (alphanumeric, max 100 chars) - DT03
  - [ ] Cantidad Recibida (numeric > 0, 8.2 decimals) - DT04
  - [ ] Unidad de Medida (dropdown: Unidades, Kg, Lts, Paquetes, Cajas, Rollos, Galones) - DT05
  - [ ] Fecha de Recepción (DD/MM/YYYY, not future) - DT01
  - [ ] Proveedor (optional)
  - [ ] Número de Factura (optional)
  - [ ] Costo Unitario (optional - LG08)
- [ ] Barcode/QR scanning integration (SIAM-RF-01, RE-03)
- [ ] Entry must be registered within 2 hours of reception (RE-01)
- [ ] Validation logic:
  - [ ] Quantity > 0 (LG01) → MS02 on failure
  - [ ] Date not future (LG02) → MS03 on failure
  - [ ] Unique ID for new materials (LG03) → MS04 on failure
  - [ ] Required fields check → MS01 on failure
- [ ] Stock update: `Nuevo Stock = Stock Actual + Cantidad Recibida` (FC01)
- [ ] Cost calculation: `Costo Total = Cantidad × Costo Unitario` (FC02)
- [ ] Transaction logging with user, timestamp, details (LG04, LG07)
- [ ] Confirmation dialog: MS05
- [ ] Success message on completion

### 2.2 CUN-002 / CU-002: Registrar Salida de Material
**Actors:** Encargado de Almacén, Jefe de Cocina

- [ ] Material exit form screen
- [ ] Validation: cannot exit more than available stock
- [ ] Stock update: `Nuevo Stock = Stock Actual - Cantidad Salida`
- [ ] Associate exit with destination (kitchen dispatch)
- [ ] Check if item is "En mantenimiento" - block if so (RE-04)
- [ ] Transaction logging
- [ ] Trigger stock alert check after exit

### 2.3 CUN-003 / CU-003: Consultar Stock Actual
**Actors:** All actors

- [ ] Inventory consultation screen
- [ ] Display material list with current quantities
- [ ] Search/filter by name, code, category
- [ ] Show physical location in warehouse (SIAM-RF-03)
- [ ] Real-time stock display
- [ ] Material status indicator (Disponible, En Mantenimiento, Dado de Baja)

### 2.4 CUN-004 / CU-004: Generar Reporte de Consumo
**Actors:** Supervisor, Departamento Compras

- [ ] Reports generation screen
- [ ] Daily/weekly/monthly consumption reports (SIAM-RF-04)
- [ ] Historical comparison with trend graphs
- [ ] Export to Excel functionality
- [ ] Inventory rotation indicators
- [ ] Service level indicators

### 2.5 CUN-005 / CU-005: Gestionar Alertas de Stock
**Actors:** Supervisor, Departamento Compras

- [ ] Stock monitoring service
- [ ] Alert when stock reaches 15% of max capacity (SIAM-RF-02)
- [ ] Configurable threshold per material
- [ ] Push notifications / email alerts
- [ ] Alert dashboard
- [ ] Automatic restock request generation

### 2.6 CUN-006 / CU-006: Registrar Estado de Equipo
**Actors:** Encargado de Almacén, Jefe de Cocina

- [ ] Equipment status screen
- [ ] Status options: Disponible, En Mantenimiento, Dado de Baja (SIAM-RF-06)
- [ ] Equipment code and maintenance date tracking
- [ ] Repair history log
- [ ] Automatic preventive maintenance order 30 days before service date (RE-05)
- [ ] Block operations on items "En mantenimiento" until order complete (RE-04)

### 2.7 Additional: Desincorporar Ítem (CUN-004 from MCUN)
- [ ] Item decommissioning workflow
- [ ] Reason documentation
- [ ] Audit trail for decommissioned items

---

## Phase 3: UI/UX Implementation

### 3.1 Mobile UI - Android (vista/mobile.kv)
- [ ] Login screen
- [ ] Main menu with navigation to all functions
- [ ] Material entry form with barcode scanner
- [ ] Material exit form
- [ ] Stock consultation with search
- [ ] Equipment status screen
- [ ] Spanish interface with intuitive icons (SIAM-RN-01)
- [ ] Touch-friendly for tablets in warehouse/kitchen (SIAM-RF-07)

### 3.2 Desktop UI - PC (vista/pc.kv)
- [ ] Admin dashboard with overview
- [ ] User management (Gestión de Usuarios)
- [ ] Reports generation (Reportes Globales)
- [ ] Database management interface
- [ ] Alert configuration panel
- [ ] Material/category CRUD

### 3.3 Responsive Design
- [ ] Tablet compatibility for warehouse and kitchen use (SIAM-RU-07)
- [ ] Consistent experience across platforms

---

## Phase 4: Model & Controller Layer (MVC from DAS)

### 4.1 Model Classes
Based on DAS diagram:

- [ ] `Material` class
  - Attributes: idMaterial, nombre, descripcion, cantidadActual, unidadMedida, stockMinimo
  - Methods: crearMaterial(), actualizarMaterial(), eliminarMaterial()

- [ ] `Usuario` class
  - Attributes: idUsuario, nombreUsuario, contrasena, rol
  - Methods: iniciarSesion(), cerrarSesion()

- [ ] `Movimiento` class
  - Attributes: idMovimiento, idMaterial, tipoMovimiento, cantidad, fecha
  - Methods: registrarMovimiento()

### 4.2 Controller Classes
Based on DAS diagram:

- [ ] `ControladorMaterial`
  - Methods: gestionarMaterial(), registrarMaterial(), actualizarMaterial()

- [ ] `ControladorUsuario`
  - Methods: gestionarUsuario(), iniciarSesion(), cerrarSesion()

- [ ] `ControladorMovimiento`
  - Methods: gestionarMovimiento(), registrarEntrada(), registrarSalida()

### 4.3 Data Access Layer
- [ ] MaterialDAO
- [ ] UsuarioDAO
- [ ] MovimientoDAO
- [ ] DBManager (connection pooling)

---

## Phase 5: Integration & Non-Functional Requirements

### 5.1 SAP Integration (SIAM-RC-01)
- [ ] SAP MM module integration for purchase orders
- [ ] Automatic purchase order generation on low stock

### 5.2 Hardware Integration (SIAM-RC-05)
- [ ] Honeywell 1900 barcode reader compatibility
- [ ] Camera-based QR/barcode scanning fallback

### 5.3 Performance (SIAM-RN-02, SIAM-RN-05)
- [ ] Response time ≤ 1.5 seconds for register/query operations
- [ ] Support 50 concurrent users without degradation

### 5.4 Security (SIAM-RN-04)
- [ ] AES-256 encryption for user data and transactions
- [ ] Audit trail for all modifications (LG07, RE-06)
- [ ] Secure session handling

### 5.5 Availability (SIAM-RN-03)
- [ ] 99.7% availability during business hours (6:00 AM - 8:00 PM)

### 5.6 Deployment (SIAM-RC-02)
- [ ] Ubuntu 22.04 LTS server deployment
- [ ] Buildozer configuration for Android APK
- [ ] Installation documentation

---

## Phase 6: Testing (from PPR and ECP)

### 6.1 Test Cases for CU-001 (Registrar Entrada)
- [ ] SIAM-CP1-CU01: Register entry of existing material with valid data
- [ ] SIAM-CP2-CU01: Register entry of new material in inventory
- [ ] SIAM-CP3-CU01: Attempt registration with invalid quantity (negative)
- [ ] SIAM-CP4-CU01: Attempt registration with future reception date

### 6.2 Test Cases for Other Use Cases
- [ ] Test cases for CU-002 (Registrar Salida)
- [ ] Test cases for CU-003 (Consultar Stock)
- [ ] Test cases for CU-004 (Generar Reporte)
- [ ] Test cases for CU-005 (Gestionar Alertas)
- [ ] Test cases for CU-006 (Registrar Estado Equipo)

### 6.3 Additional Testing
- [ ] Integration tests
- [ ] Performance tests (50 concurrent users)
- [ ] Security tests (encryption, auth)
- [ ] Usability tests (Spanish interface, workflow)

---

## Current Implementation Status

### Completed
- [x] Basic MVC folder structure (controlador/, modelo/, vista/)
- [x] KivyMD app initialization with Material Design 3
- [x] Platform detection (Android/Desktop)
- [x] Camera screen with pyzbar barcode scanning
- [x] DummyDatabase for development testing
- [x] Basic navigation (mobile bottom bar)
- [x] CORPOELEC corporate colors (Blue #001A70, Red #E31C23)

### In Progress
- [ ] (None currently)

### Priority for Next Sprint
1. PostgreSQL database implementation (Phase 1.1)
2. CU-001: Material entry form and logic (Phase 2.1)
3. Authentication system (Phase 1.2)
4. Material entry barcode scanning integration

---

## Business Rules Summary (from MDN RE-01 to RE-06)

| ID | Rule |
|----|------|
| RE-01 | Entry must be registered within 2 hours of reception |
| RE-02 | Maintain inventory history for at least 5 years |
| RE-03 | Must scan QR/barcode before any entry/exit operation |
| RE-04 | Cannot process items with status "En mantenimiento" |
| RE-05 | Auto-generate preventive maintenance order 30 days before service |
| RE-06 | Full traceability (user, date, action) for all transactions |
