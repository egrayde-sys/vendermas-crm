"""
migrar_renovaciones.py — Ejecutar UNA sola vez
Genera todas las renovaciones para cada cliente desde su fecha de inicio
hasta 6 semanas adelante.
"""

from google.oauth2.service_account import Credentials
import gspread
from datetime import date, datetime, timedelta
import uuid

SHEET_ID    = '1QIAdGEzZu2_bLOqYLIPTc2F5KFG5kWXO1oERaGolluc'
CREDENTIALS = 'vendermas-ads-3859a86efed0.json'
SCOPES      = ['https://www.googleapis.com/auth/spreadsheets','https://www.googleapis.com/auth/drive']

def get_sheet():
    creds = Credentials.from_service_account_file(CREDENTIALS, scopes=SCOPES)
    return gspread.authorize(creds).open_by_key(SHEET_ID)

def mes_label(d):
    meses = ['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic']
    return f"{meses[d.month-1]}-{str(d.year)[2:]}"

def siguiente_fecha_mensual(fecha, dia_vencimiento):
    """Siguiente fecha manteniendo el día de vencimiento"""
    mes = fecha.month + 1
    anio = fecha.year
    if mes > 12:
        mes = 1
        anio += 1
    import calendar
    ultimo = calendar.monthrange(anio, mes)[1]
    dia = min(dia_vencimiento, ultimo)
    return date(anio, mes, dia)

def main():
    print('\n🚀 Iniciando migración de renovaciones...\n')
    sh = get_sheet()
    ws_cli = sh.worksheet('Clientes')
    ws_ren = sh.worksheet('Renovaciones')

    clientes = ws_cli.get_all_records()
    renovaciones_existentes = ws_ren.get_all_records()

    # Crear set de renovaciones existentes (id_cliente + mes)
    existentes = set()
    for r in renovaciones_existentes:
        key = f"{r.get('ID Cliente','')}-{r.get('Mes','')}"
        existentes.add(key)

    hoy = date.today()
    fecha_limite = hoy + timedelta(weeks=6)

    nuevas = []
    total = 0

    for c in clientes:
        estado = c.get('Estado','').strip().lower()
        if estado == 'perdido':
            continue

        cid          = c.get('ID','')
        nombre       = c.get('Nombre','')
        fecha_inicio_str = c.get('Fecha Inicio','')
        dia_v        = c.get('Día Vencimiento','')
        frecuencia   = c.get('Frecuencia','mensual') if c.get('Frecuencia') else 'mensual'
        monto        = c.get('Monto',0)

        if not fecha_inicio_str or not dia_v:
            print(f'  ⚠️  Saltando {nombre} — sin fecha inicio o día vencimiento')
            continue

        try:
            fecha_inicio = datetime.strptime(str(fecha_inicio_str), '%Y-%m-%d').date()
            dia_venc = int(str(dia_v))
        except:
            print(f'  ⚠️  Error parseando fechas de {nombre}')
            continue

        # Primera fecha de vencimiento = fecha inicio con el día de vencimiento
        import calendar
        ultimo = calendar.monthrange(fecha_inicio.year, fecha_inicio.month)[1]
        dia_real = min(dia_venc, ultimo)
        fecha_actual = date(fecha_inicio.year, fecha_inicio.month, dia_real)

        # Si el día de vencimiento ya pasó en el mes de inicio, ir al siguiente mes
        if fecha_actual < fecha_inicio:
            fecha_actual = siguiente_fecha_mensual(fecha_actual, dia_venc)

        count_cliente = 0
        while fecha_actual <= fecha_limite:
            mes = mes_label(fecha_actual)
            key = f"{cid}-{mes}"

            if key not in existentes:
                # Determinar estado
                if fecha_actual < hoy:
                    estado_ren = 'vencido'
                else:
                    estado_ren = 'pendiente'

                rid = 'r' + str(uuid.uuid4())[:6]
                nuevas.append([
                    rid, cid, nombre, mes, estado_ren,
                    '', '',  # fecha renovación, fecha pago
                    monto, '', '',  # valor campaña, comisión, monto ads
                    '', '',  # factura, banco
                    frecuencia, str(fecha_actual), ''  # frecuencia, fecha vencimiento, fecha postergación
                ])
                existentes.add(key)
                count_cliente += 1

            # Avanzar al siguiente período
            if frecuencia == 'semanal':
                fecha_actual = fecha_actual + timedelta(days=7)
            else:
                fecha_actual = siguiente_fecha_mensual(fecha_actual, dia_venc)

        total += count_cliente
        print(f'  ✓ {nombre}: {count_cliente} renovaciones generadas')

    if nuevas:
        print(f'\n📝 Insertando {len(nuevas)} renovaciones en el Sheet...')
        # Insertar en lotes de 50 para no exceder límites
        for i in range(0, len(nuevas), 50):
            lote = nuevas[i:i+50]
            ws_ren.append_rows(lote, value_input_option='USER_ENTERED')
            print(f'  Lote {i//50 + 1} insertado ({len(lote)} filas)')
        print(f'\n✅ Migración completa — {total} renovaciones generadas')
    else:
        print('\n✅ No hay renovaciones nuevas que generar')

if __name__ == '__main__':
    main()
