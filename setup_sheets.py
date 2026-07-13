"""
setup_sheets.py — Inicializa el Google Sheet de Vendermas CRM
Ejecutar UNA sola vez para crear la estructura completa.
"""

import gspread
from google.oauth2.service_account import Credentials
from datetime import date, datetime
import os

# ============================================================
SHEET_ID       = '1QIAdGEzZu2_bLOqYLIPTc2F5KFG5kWXO1oERaGolluc'
CREDENTIALS    = 'vendermas-ads-3859a86efed0.json'
# ============================================================

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

def conectar():
    creds = Credentials.from_service_account_file(CREDENTIALS, scopes=SCOPES)
    return gspread.authorize(creds)

def limpiar_o_crear(sh, nombre):
    try:
        ws = sh.worksheet(nombre)
        ws.clear()
        print(f'  ✓ Pestaña "{nombre}" limpiada')
    except:
        ws = sh.add_worksheet(title=nombre, rows=500, cols=30)
        print(f'  ✓ Pestaña "{nombre}" creada')
    return ws

def col_letter(n):
    s = ''
    while n > 0:
        n, r = divmod(n-1, 26)
        s = chr(65+r) + s
    return s

def formato_header(ws, n_cols):
    ultima_col = col_letter(n_cols)
    ws.format(f'A1:{ultima_col}1', {
        'backgroundColor': {'red': 0.016, 'green': 0.173, 'blue': 0.325},
        'textFormat': {'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}, 'bold': True, 'fontSize': 10},
        'horizontalAlignment': 'CENTER'
    })

def setup_clientes(sh):
    ws = limpiar_o_crear(sh, 'Clientes')
    headers = [
        'ID', 'Nombre', 'Contacto', 'Email', 'Teléfono', 'Web', 'Rubro',
        'Plan', 'Monto', 'Inversión Ads', 'Rentabilidad',
        'Fecha Inicio', 'Día Vencimiento', 'Tipo Pago', 'ID Google Ads', 'Estado'
    ]
    ws.append_row(headers)
    formato_header(ws, len(headers))

    clientes = [
        ['c1','DIAMETEC','Juan Díaz','juan@diametec.cl','+56911111111','diametec.cl','Industrial','Premium Plus',340990,273000,'=I2-J2','2025-01-15',15,'factura','1234567890','activo'],
        ['c2','Dental Sonrisa','María González','maria@dentalsonrisa.cl','+56922222222','dentalsonrisa.cl','Salud','Premium',202990,162000,'=I3-J3','2025-03-01',1,'factura','2345678901','activo'],
        ['c3','Constructora Andina','Roberto Muñoz','roberto@constructoraandina.cl','+56933333333','constructoraandina.cl','Construcción','Base Plus',149990,119000,'=I4-J4','2025-08-10',10,'negro','3456789012','activo'],
        ['c4','Clínica Bienestar','Carmen Vidal','carmen@clinicabienestar.cl','+56944444444','clinicabienestar.cl','Salud','Base Plus',149990,119000,'=I5-J5','2026-05-20',20,'factura','4567890123','activo'],
        ['c5','Ferretería Central','Hugo Rojas','hugo@ferreteriacentral.cl','+56955555555','ferreteriacentral.cl','Retail','Base',89990,71000,'=I6-J6','2024-11-05',5,'negro','5678901234','activo'],
        ['c6','Viajes Aventura','Sofía Castro','sofia@viajesaventura.cl','+56966666666','viajesaventura.cl','Turismo','Premium',202990,162000,'=I7-J7','2025-06-15',15,'factura','6789012345','activo'],
        ['c7','Abogados Torres','Felipe Torres','felipe@abogadostorres.cl','+56977777777','abogadostorres.cl','Legal','Base',89990,71000,'=I8-J8','2025-09-20',20,'factura','7890123456','activo'],
        ['c8','RestoCentro','Patricia Leal','patricia@restocentro.cl','+56988888888','restocentro.cl','Gastronomía','Administración',95990,0,'=I9-J9','2025-04-12',12,'negro','8901234567','activo'],
    ]
    for row in clientes:
        ws.append_row(row, value_input_option='USER_ENTERED')

    # Ancho de columnas
    print(f'  ✓ {len(clientes)} clientes ingresados')

def setup_leads(sh):
    ws = limpiar_o_crear(sh, 'Leads')
    headers = [
        'ID', 'Nombre Empresa', 'Contacto', 'Email', 'Teléfono', 'Web',
        'Fuente', 'Plan Interés', 'Monto Estimado', 'Etapa',
        'Fecha Creación', 'Fecha Contacto', 'Notas'
    ]
    ws.append_row(headers)
    formato_header(ws, len(headers))

    leads = [
        ['l1','Constructora Lagos','Mario Lagos','mario@constructoralagos.cl','+56912345678','constructoralagos.cl','Google Ads','Premium',202990,'negociacion','2026-05-28','2026-05-29','Interesado en plan Premium'],
        ['l2','Dental Providencia','Ana Muñoz','ana@dentalprovidencia.cl','+56923456789','dentalprovidencia.cl','Facebook Ads','Base Plus',149990,'contactado','2026-06-01','2026-06-02','Llamar martes'],
        ['l3','Ferretería El Tornillo','Pedro Soto','pedro@eltornillo.cl','+56934567890','eltornillo.cl','Google Ads','Base',89990,'nuevo','2026-06-03','',''],
        ['l4','Tech Solutions','Carlos Mora','carlos@techsolutions.cl','+56978901234','techsolutions.cl','Google Ads','Premium Plus',340990,'negociacion','2026-06-02','2026-06-03','Evalúa plan Premium Plus'],
        ['l5','Auto Express','Luis Pérez','luis@autoexpress.cl','+56956789012','autoexpress.cl','Facebook Ads','Base',89990,'perdido','2026-05-15','2026-05-16','Eligió competencia'],
    ]
    for row in leads:
        ws.append_row(row, value_input_option='USER_ENTERED')

    print(f'  ✓ {len(leads)} leads ingresados')

def setup_renovaciones(sh):
    ws = limpiar_o_crear(sh, 'Renovaciones')
    headers = [
        'ID', 'ID Cliente', 'Nombre Cliente', 'Mes', 'Estado',
        'Fecha Renovación', 'Fecha Pago', 'Valor Campaña', 'Comisión',
        'Monto Ads', 'N° Factura', 'Banco'
    ]
    ws.append_row(headers)
    formato_header(ws, len(headers))

    renovaciones = [
        ['r001','c1','DIAMETEC','ene-26','renovado','2026-01-14','2026-01-14',340990,68198,273000,'F-001','Banco Chile'],
        ['r002','c1','DIAMETEC','feb-26','renovado','2026-02-13','2026-02-14',340990,68198,273000,'F-012','Banco Chile'],
        ['r003','c1','DIAMETEC','mar-26','renovado','2026-03-15','2026-03-15',340990,68198,273000,'F-023','Banco Chile'],
        ['r004','c1','DIAMETEC','abr-26','renovado','2026-04-14','2026-04-15',345000,69000,273000,'F-034','Banco Chile'],
        ['r005','c1','DIAMETEC','may-26','renovado','2026-05-15','2026-05-15',340990,68198,273000,'F-045','Banco Chile'],
        ['r006','c1','DIAMETEC','jun-26','pendiente','','','','','','',''],
        ['r007','c2','Dental Sonrisa','ene-26','renovado','2026-01-01','2026-01-02',202990,40598,162000,'F-002','Santander'],
        ['r008','c2','Dental Sonrisa','feb-26','renovado','2026-02-01','2026-02-01',202990,40598,162000,'F-013','Santander'],
        ['r009','c2','Dental Sonrisa','mar-26','renovado','2026-03-01','2026-03-03',202990,40598,162000,'F-024','Santander'],
        ['r010','c2','Dental Sonrisa','abr-26','renovado','2026-04-01','2026-04-01',202990,40598,162000,'F-035','Santander'],
        ['r011','c2','Dental Sonrisa','may-26','renovado','2026-05-01','2026-05-02',202990,40598,162000,'F-046','Santander'],
        ['r012','c2','Dental Sonrisa','jun-26','pendiente','','','','','','',''],
        ['r013','c3','Constructora Andina','ene-26','renovado','2026-01-10','2026-01-10',149990,29998,119000,'','Efectivo'],
        ['r014','c3','Constructora Andina','feb-26','renovado','2026-02-10','2026-02-10',149990,29998,119000,'','Efectivo'],
        ['r015','c3','Constructora Andina','mar-26','renovado','2026-03-11','2026-03-11',149990,29998,119000,'','Efectivo'],
        ['r016','c3','Constructora Andina','abr-26','atrasado','2026-04-18','2026-04-20',149990,29998,119000,'','Efectivo'],
        ['r017','c3','Constructora Andina','may-26','renovado','2026-05-10','2026-05-10',149990,29998,119000,'','Efectivo'],
        ['r018','c3','Constructora Andina','jun-26','pendiente','','','','','','',''],
        ['r019','c5','Ferretería Central','ene-26','renovado','2026-01-05','2026-01-05',89990,17998,71000,'','Transferencia'],
        ['r020','c5','Ferretería Central','feb-26','renovado','2026-02-05','2026-02-05',89990,17998,71000,'','Transferencia'],
        ['r021','c5','Ferretería Central','mar-26','renovado','2026-03-05','2026-03-05',89990,17998,71000,'','Transferencia'],
        ['r022','c5','Ferretería Central','abr-26','renovado','2026-04-05','2026-04-06',89990,17998,71000,'','Transferencia'],
        ['r023','c5','Ferretería Central','may-26','renovado','2026-05-05','2026-05-05',89990,17998,71000,'','Transferencia'],
        ['r024','c5','Ferretería Central','jun-26','pendiente','','','','','','',''],
    ]
    for row in renovaciones:
        ws.append_row(row, value_input_option='USER_ENTERED')

    print(f'  ✓ {len(renovaciones)} renovaciones ingresadas')

def setup_metas(sh):
    ws = limpiar_o_crear(sh, 'Metas')

    # Sección 1 — Metas mensuales
    ws.append_row(['METAS MENSUALES'])
    ws.format('A1', {'textFormat': {'bold': True, 'fontSize': 11}})
    ws.append_row([])
    ws.append_row(['Mes', 'Meta Clientes Nuevos', 'Meta Clientes Nuevos (Sistema)', 'Meta Renovaciones', 'Meta Renovaciones (Sistema)', 'Meta Monto Captación', 'Meta Monto Captación (Sistema)', 'Meta Monto Renovación', 'Meta Monto Renovación (Sistema)'])
    formato_header(ws, 9)

    metas = [
        ['ene-26', 3, 3, 42, 44, 267000, 280000, 11500000, 11800000],
        ['feb-26', 2, 3, 38, 44, 178000, 280000, 10900000, 11800000],
        ['mar-26', 4, 3, 41, 44, 356000, 280000, 11600000, 11800000],
        ['abr-26', 3, 3, 46, 44, 267000, 280000, 12000000, 11800000],
        ['may-26', 2, 3, 45, 44, 178000, 280000, 11400000, 11800000],
        ['jun-26', '', 3, '', 44, '', 280000, '', 11800000],
    ]
    for row in metas:
        ws.append_row(row, value_input_option='USER_ENTERED')

    ws.append_row([])
    ws.append_row([])

    # Sección 2 — Metas por plan
    fila_actual = len(metas) + 6
    ws.update_cell(fila_actual, 1, 'METAS POR PLAN')
    ws.format(f'A{fila_actual}', {'textFormat': {'bold': True, 'fontSize': 11}})
    ws.append_row([])
    ws.append_row(['Plan', 'Monto Promedio Esperado', 'Meta Clientes / Mes', 'Clientes Actuales'])
    formato_header(ws, 4)

    planes = [
        ['Base', 89990, 1, 2],
        ['Base Plus', 149990, 1, 2],
        ['Premium', 202990, 1, 2],
        ['Premium Plus', 340990, 1, 1],
        ['Administración', 95990, 0, 1],
    ]
    for row in planes:
        ws.append_row(row, value_input_option='USER_ENTERED')

    print(f'  ✓ Metas configuradas')

def main():
    print('\n🚀 Inicializando Vendermas CRM en Google Sheets...\n')

    gc = conectar()
    sh = gc.open_by_key(SHEET_ID)
    print(f'✓ Conectado a: {sh.title}\n')

    # Eliminar hoja por defecto si existe
    try:
        hoja1 = sh.worksheet('Hoja 1')
        sh.del_worksheet(hoja1)
    except:
        pass
    try:
        hoja1 = sh.worksheet('Sheet1')
        sh.del_worksheet(hoja1)
    except:
        pass

    print('Creando pestañas...')
    setup_clientes(sh)
    setup_leads(sh)
    setup_renovaciones(sh)
    setup_metas(sh)

    print(f'\n✅ Sheet inicializado correctamente')
    print(f'🔗 https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit\n')

if __name__ == '__main__':
    main()
