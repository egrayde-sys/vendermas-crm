from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
import gspread, os, html
from datetime import date, timedelta, datetime
import uuid, calendar
from google.ads.googleads.client import GoogleAdsClient
import yaml

load_dotenv()
LOGIN_USER = os.getenv('LOGIN_USER', 'admin')
LOGIN_PASSWORD = os.getenv('LOGIN_PASSWORD', 'vendermas2026')

app = Flask(__name__, static_folder='static')
CORS(app)
limiter = Limiter(get_remote_address, app=app, default_limits=["200 per minute"])

SHEET_ID    = os.getenv('SHEET_ID', '1QIAdGEzZu2_bLOqYLIPTc2F5KFG5kWXO1oERaGolluc')
CREDENTIALS = os.getenv('CREDENTIALS', 'vendermas-ads-3859a86efed0.json')
SCOPES      = ['https://www.googleapis.com/auth/spreadsheets','https://www.googleapis.com/auth/drive']

def get_sheet():
    import json as _json, base64
    creds_b64 = os.getenv('GOOGLE_CREDENTIALS_B64')
    creds_json = os.getenv('GOOGLE_CREDENTIALS_JSON')
    if creds_b64:
        try:
            creds_info = _json.loads(base64.b64decode(creds_b64).decode('utf-8'))
            creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
            print('Credentials loaded from B64')
        except Exception as e:
            print(f'ERROR parsing GOOGLE_CREDENTIALS_B64: {e}')
            raise
    elif creds_json:
        try:
            creds_info = _json.loads(creds_json)
            creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
            print('Credentials loaded from JSON')
        except Exception as e:
            print(f'ERROR parsing GOOGLE_CREDENTIALS_JSON: {e}')
            raise
    else:
        print(f'WARNING: No credentials env var set, using file: {CREDENTIALS}')
        creds = Credentials.from_service_account_file(CREDENTIALS, scopes=SCOPES)
    return gspread.authorize(creds).open_by_key(SHEET_ID)

def sheet_to_dicts(ws):
    rows = ws.get_all_values()
    if len(rows) < 2: return []
    headers = rows[0]
    return [dict(zip(headers, row)) for row in rows[1:] if any(cell.strip() for cell in row)]

def parse_int(v):
    try: return int(str(v).replace('.','').replace(',','').replace('$','').strip())
    except: return 0

def mes_label(d):
    meses = ['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic']
    return meses[d.month-1]

def sig_fecha_desde_pago(fecha_pago, freq):
    if freq == 'semanal':
        return fecha_pago + timedelta(days=7)
    elif freq == 'quincenal':
        return fecha_pago + timedelta(days=15)
    else:
        mes = fecha_pago.month + 1
        anio = fecha_pago.year
        if mes > 12: mes = 1; anio += 1
        ultimo = calendar.monthrange(anio, mes)[1]
        return date(anio, mes, min(fecha_pago.day, ultimo))

from functools import wraps
from flask import session

app.secret_key = os.getenv('SECRET_KEY', 'vendermas-secret-2026')

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return jsonify({'error': 'No autorizado'}), 401
        return f(*args, **kwargs)
    return decorated

@app.route('/api/login', methods=['POST'])
def login():
    d = request.json
    if d.get('usuario') == LOGIN_USER and d.get('password') == LOGIN_PASSWORD:
        session['logged_in'] = True
        return jsonify({'ok': True})
    return jsonify({'error': 'Credenciales incorrectas'}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'ok': True})

@app.route('/api/check_auth')
def check_auth():
    return jsonify({'logged_in': session.get('logged_in', False)})

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/api/clientes')
@login_required
def get_clientes():
    try:
        sh = get_sheet()
        rows = sheet_to_dicts(sh.worksheet('Clientes'))
        result = []
        for r in rows:
            if not r.get('Estado','').strip(): continue
            monto = parse_int(r.get('Monto',0))
            inv   = parse_int(r.get('Inversión Ads',0))
            result.append({
                'id': r.get('ID',''), 'nombre': r.get('Nombre',''),
                'contacto': r.get('Contacto',''), 'email': r.get('Email',''),
                'telefono': r.get('Teléfono',''), 'web': r.get('Web',''),
                'rubro': r.get('Rubro',''), 'plan': r.get('Plan',''),
                'monto': monto, 'inversion_ads': inv, 'rentabilidad': monto-inv,
                'fecha_inicio': r.get('Fecha Inicio',''),
                'tipo_pago': r.get('Tipo Pago',''),
                'google_ads_id': r.get('ID Google Ads',''),
                'fecha_perdido': r.get('Fecha Perdido',''),
                'estado': r.get('Estado','').strip().lower(),
            })
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/clientes/<cid>')
@login_required
def get_cliente(cid):
    try:
        sh = get_sheet()
        rows = sheet_to_dicts(sh.worksheet('Clientes'))
        c = next((r for r in rows if r.get('ID') == cid), None)
        if not c: return jsonify({'error': 'No encontrado'}), 404
        ren_rows = sheet_to_dicts(sh.worksheet('Renovaciones'))
        renovaciones = []
        for r in ren_rows:
            if r.get('ID Cliente') == cid:
                renovaciones.append({
                    'id': r.get('ID',''), 'mes': r.get('Mes',''), 'anio': r.get('Año',''),
                    'estado': r.get('Estado',''), 'fecha': r.get('Fecha Renovación',''),
                    'fecha_pago': r.get('Fecha Pago',''),
                    'fecha_vencimiento': r.get('Fecha Vencimiento ','').strip(),
                    'fecha_reprogramacion': r.get('Fecha Reprogramación',''),
                    'monto': parse_int(r.get('Valor Campaña',0)),
                    'comision': parse_int(r.get('Comisión',0)),
                    'monto_ads': parse_int(r.get('Monto Ads',0)),
                    'factura': r.get('N° Factura',''), 'banco': r.get('Banco',''),
                    'frecuencia': r.get('Frecuencia','mensual'),
                })
        monto = parse_int(c.get('Monto',0))
        inv   = parse_int(c.get('Inversión Ads',0))
        return jsonify({
            'id': cid, 'nombre': c.get('Nombre',''), 'contacto': c.get('Contacto',''),
            'email': c.get('Email',''), 'telefono': c.get('Teléfono',''),
            'web': c.get('Web',''), 'rubro': c.get('Rubro',''), 'plan': c.get('Plan',''),
            'monto': monto, 'inversion_ads': inv, 'rentabilidad': monto-inv,
            'fecha_inicio': c.get('Fecha Inicio',''),
            'tipo_pago': c.get('Tipo Pago',''), 'google_ads_id': c.get('ID Google Ads',''),
            'estado': c.get('Estado',''), 'renovaciones': renovaciones
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/clientes', methods=['POST'])
@login_required
def crear_cliente():
    try:
        sh = get_sheet()
        ws = sh.worksheet('Clientes')
        d = request.json
        cid = 'c'+str(uuid.uuid4())[:6]
        monto = parse_int(d.get('monto',0))
        inv   = parse_int(d.get('inversion_ads',0))
        ws.append_row([cid, d.get('nombre',''), d.get('contacto',''), d.get('email',''),
            d.get('telefono',''), d.get('web',''), d.get('rubro',''), d.get('plan',''),
            monto, inv, monto-inv, d.get('fecha_inicio', str(date.today())),
            '', d.get('tipo_pago','factura'), d.get('google_ads_id',''), d.get('estado','activo')],
            value_input_option='USER_ENTERED')
        return jsonify({'ok': True, 'id': cid})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/clientes/<cid>', methods=['PUT'])
@login_required
def actualizar_cliente(cid):
    try:
        sh = get_sheet()
        ws = sh.worksheet('Clientes')
        rows = ws.get_all_values()
        headers = rows[0]
        campo_map = {
            'nombre':'Nombre','contacto':'Contacto','email':'Email','telefono':'Teléfono',
            'web':'Web','rubro':'Rubro','plan':'Plan','monto':'Monto',
            'inversion_ads':'Inversión Ads','fecha_inicio':'Fecha Inicio',
            'tipo_pago':'Tipo Pago','google_ads_id':'ID Google Ads',
            'estado':'Estado','fecha_perdido':'Fecha Perdido'
        }
        for i, row in enumerate(rows[1:], start=2):
            if row[0] == cid:
                d = request.json
                for campo, header in campo_map.items():
                    if campo in d and header in headers:
                        ws.update_cell(i, headers.index(header)+1, d[campo])
                return jsonify({'ok': True})
        return jsonify({'error': 'No encontrado'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/leads')
@login_required
def get_leads():
    try:
        sh = get_sheet()
        rows = sheet_to_dicts(sh.worksheet('Leads'))
        return jsonify([{
            'id': r.get('ID',''), 'nombre': r.get('Nombre Empresa',''),
            'contacto': r.get('Contacto',''), 'email': r.get('Email',''),
            'telefono': r.get('Teléfono',''), 'web': r.get('Web',''),
            'fuente': r.get('Fuente',''), 'plan_interes': r.get('Plan Interés',''),
            'monto_estimado': parse_int(r.get('Monto Estimado',0)),
            'etapa': r.get('Etapa',''), 'fecha': r.get('Fecha Creación',''),
            'fecha_contacto': r.get('Fecha Contacto',''), 'notas': r.get('Notas',''),
            'fecha_venta': r.get('Fecha Venta',''), 'motivo_rechazo': r.get('Motivo Rechazo',''),
            'comentarios': r.get('Comentarios',''), 'fecha_perdido':  r.get('Fecha Perdido',''),
            'fecha_proximo_contacto': r.get('Fecha Próximo Contacto',''),
        } for r in rows if r.get('Nombre Empresa','').strip()])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/leads', methods=['POST'])
@login_required
def crear_lead():
    try:
        sh = get_sheet()
        ws = sh.worksheet('Leads')
        d = request.json
        lid = 'l'+str(uuid.uuid4())[:6]
        ws.append_row([lid, d.get('nombre',''), d.get('contacto',''), d.get('email',''),
            d.get('telefono',''), d.get('web',''), d.get('fuente',''),
            d.get('plan_interes',''), d.get('monto_estimado',0), d.get('etapa','nuevo'),
            str(date.today()), d.get('fecha_contacto', str(date.today())), d.get('notas','')],
            value_input_option='USER_ENTERED')
        return jsonify({'ok': True, 'id': lid})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/leads/<lid>', methods=['PUT'])
@login_required
def actualizar_lead(lid):
    try:
        sh = get_sheet()
        ws = sh.worksheet('Leads')
        rows = ws.get_all_values()
        headers = rows[0]
        campo_map = {
            'nombre':'Nombre Empresa','contacto':'Contacto','email':'Email',
            'telefono':'Teléfono','web':'Web','fuente':'Fuente',
            'plan_interes':'Plan Interés','monto_estimado':'Monto Estimado',
            'etapa':'Etapa','fecha_contacto':'Fecha Contacto','notas':'Notas',
            'fecha_venta':'Fecha Venta','motivo_rechazo':'Motivo Rechazo',
            'comentarios':'Comentarios','fecha_perdido':  'Fecha Perdido',
            'fecha_proximo_contacto': 'Fecha Próximo Contacto',
        }
        for i, row in enumerate(rows[1:], start=2):
            if row[0] == lid:
                d = request.json
                for campo, header in campo_map.items():
                    if campo in d and header in headers:
                        ws.update_cell(i, headers.index(header)+1, d[campo])
                return jsonify({'ok': True})
        return jsonify({'error': 'No encontrado'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/renovaciones')
@login_required
def get_renovaciones():
    try:
        sh = get_sheet()
        ren_rows = sheet_to_dicts(sh.worksheet('Renovaciones'))
        cli_rows = sheet_to_dicts(sh.worksheet('Clientes'))
        cli_dict = {c.get('ID',''):c for c in cli_rows}
        hoy = date.today()
        result = []
        for r in ren_rows:
            cid = r.get('ID Cliente','')
            cli = cli_dict.get(cid,{})
            fv_str = r.get('Fecha Vencimiento ','').strip()
            estado = r.get('Estado','pendiente').strip()
            if fv_str and estado == 'pendiente':
                try:
                    if datetime.strptime(fv_str, '%Y-%m-%d').date() < hoy:
                        estado = 'vencido'
                except: pass
            try:
                dias = (datetime.strptime(fv_str, '%Y-%m-%d').date() - hoy).days if fv_str else 99
            except: dias = 99
            result.append({
                'id': r.get('ID',''), 'id_cliente': cid,
                'nombre_cliente': r.get('Nombre Cliente','') or cli.get('Nombre',''),
                'mes': r.get('Mes',''), 'anio': r.get('Año',''),
                'estado': estado, 'fecha': r.get('Fecha Renovación',''),
                'fecha_pago': r.get('Fecha Pago',''),
                'monto': parse_int(r.get('Valor Campaña',0)) or parse_int(cli.get('Monto',0)),
                'comision': parse_int(r.get('Comisión',0)),
                'monto_ads': parse_int(r.get('Monto Ads',0)),
                'factura': r.get('N° Factura',''), 'banco': r.get('Banco',''),
                'frecuencia': r.get('Frecuencia','mensual'),
                'fecha_vencimiento': fv_str,
                'fecha_reprogramacion': r.get('Fecha Reprogramación',''),
                'plan': cli.get('Plan',''), 'contacto': cli.get('Contacto',''),
                'telefono': cli.get('Teléfono',''), 'email': cli.get('Email',''),
                'dias': dias,
            })
        result.sort(key=lambda x: x['fecha_vencimiento'] or '9999')
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/renovaciones', methods=['POST'])
@login_required
def crear_renovacion():
    try:
        sh = get_sheet()
        ws = sh.worksheet('Renovaciones')
        d = request.json
        rid = 'r'+str(uuid.uuid4())[:6]
        ws.append_row([
            rid, d.get('id_cliente',''), d.get('nombre_cliente',''),
            d.get('mes',''), d.get('anio',''),
            d.get('estado','pendiente'), d.get('fecha',''),
            d.get('fecha_pago',''), d.get('monto',0), d.get('comision',0),
            d.get('monto_ads',0), d.get('factura',''), d.get('banco',''),
            d.get('frecuencia','mensual'), d.get('fecha_vencimiento',''),
            d.get('fecha_reprogramacion','')
        ], value_input_option='USER_ENTERED')
        return jsonify({'ok':True,'id':rid})
    except Exception as e:
        return jsonify({'error':str(e)}), 500

@app.route('/api/renovaciones/<rid>', methods=['PUT'])
@login_required
def actualizar_renovacion(rid):
    try:
        sh = get_sheet()
        ws = sh.worksheet('Renovaciones')
        rows = ws.get_all_values()
        headers = rows[0]
        campo_map = {
            'estado':'Estado','fecha':'Fecha Renovación','fecha_pago':'Fecha Pago',
            'monto':'Valor Campaña','comision':'Comisión','monto_ads':'Monto Ads',
            'factura':'N° Factura','banco':'Banco','frecuencia':'Frecuencia',
            'anio':'Año','fecha_vencimiento':'Fecha Vencimiento ',
            'fecha_reprogramacion':'Fecha Reprogramación'
        }
        for i, row in enumerate(rows[1:], start=2):
            if row[0] == rid:
                d = request.json
                for campo, header in campo_map.items():
                    if campo in d and header in headers:
                        ws.update_cell(i, headers.index(header)+1, d[campo])
                return jsonify({'ok': True})
        return jsonify({'error': 'No encontrado'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/renovaciones/<rid>/pagar', methods=['POST'])
@login_required
def pagar_renovacion(rid):
    try:
        sh = get_sheet()
        ws = sh.worksheet('Renovaciones')
        rows = ws.get_all_values()
        headers = rows[0]
        d = request.json
        fecha_pago_str = d.get('fecha_pago', str(date.today()))
        try:
            fecha_pago = datetime.strptime(fecha_pago_str, '%Y-%m-%d').date()
        except:
            fecha_pago = date.today()
        for i, row in enumerate(rows[1:], start=2):
            if row[0] == rid:
                ws.update_cell(i, headers.index('Estado')+1, 'renovado')
                ws.update_cell(i, headers.index('Fecha Pago')+1, fecha_pago_str)
                freq = row[headers.index('Frecuencia')] if 'Frecuencia' in headers else 'mensual'
                sig = sig_fecha_desde_pago(fecha_pago, freq)
                sig_mes = mes_label(sig)
                sig_anio = str(sig.year)
                id_cliente = row[headers.index('ID Cliente')] if 'ID Cliente' in headers else ''
                nombre_cliente = row[headers.index('Nombre Cliente')] if 'Nombre Cliente' in headers else ''
                monto = row[headers.index('Valor Campaña')] if 'Valor Campaña' in headers else 0
                new_rid = 'r'+str(uuid.uuid4())[:6]
                ws.append_row([
                    new_rid, id_cliente, nombre_cliente, sig_mes, sig_anio,
                    'pendiente', '', '', monto, '', '', '', '', freq, str(sig), ''
                ], value_input_option='USER_ENTERED')
                return jsonify({'ok':True,'siguiente_fecha':str(sig),'siguiente_mes':f"{sig_mes}-{sig_anio[2:]}"})
        return jsonify({'error':'No encontrado'}), 404
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error':str(e)}), 500

@app.route('/api/renovaciones/<rid>/reprogramar', methods=['POST'])
@login_required
def reprogramar_renovacion(rid):
    try:
        sh = get_sheet()
        ws = sh.worksheet('Renovaciones')
        rows = ws.get_all_values()
        headers = rows[0]
        d = request.json
        nueva_fecha = d.get('fecha_reprogramacion','')
        for i, row in enumerate(rows[1:], start=2):
            if row[0] == rid:
                if 'Fecha Reprogramación' in headers:
                    ws.update_cell(i, headers.index('Fecha Reprogramación')+1, nueva_fecha)
                ws.update_cell(i, headers.index('Estado')+1, 'reprogramado')
                return jsonify({'ok':True})
        return jsonify({'error':'No encontrado'}), 404
    except Exception as e:
        return jsonify({'error':str(e)}), 500

@app.route('/api/resumen')
@login_required
def get_resumen():
    try:
        sh = get_sheet()
        clientes = sheet_to_dicts(sh.worksheet('Clientes'))
        leads    = sheet_to_dicts(sh.worksheet('Leads'))
        activos  = [c for c in clientes if c.get('Estado','').strip().lower() != 'perdido']
        ingresos = sum(parse_int(c.get('Monto',0)) for c in activos)
        inversion= sum(parse_int(c.get('Inversión Ads',0)) for c in activos)
        leads_activos  = sum(1 for l in leads if l.get('Etapa') not in ['cerrado','perdido'])
        leads_cerrados = sum(1 for l in leads if l.get('Etapa') == 'cerrado')
        return jsonify({
            'clientes_activos': len(activos), 'ingresos_mes': ingresos,
            'margen_mes': ingresos-inversion, 'vencen_semana': 0,
            'leads_activos': leads_activos, 'leads_cerrados': leads_cerrados,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/metas')
@login_required
def get_metas():
    try:
        sh = get_sheet()
        rows = sh.worksheet('Metas').get_all_values()
        metas = []
        for i, row in enumerate(rows):
            if row and row[0] == 'Mes':
                for r in rows[i+1:]:
                    if r and r[0].strip():
                        metas.append({
                            'mes': r[0],
                            'meta_nuevos': parse_int(r[1]) if len(r)>1 else 0,
                            'real_nuevos': parse_int(r[2]) if len(r)>2 else 0,
                            'meta_renovaciones': parse_int(r[3]) if len(r)>3 else 0,
                            'real_renovaciones': parse_int(r[4]) if len(r)>4 else 0,
                            'tiene_meta': bool(r[1].strip() if len(r)>1 else ''),
                        })
                break
        con_datos = [m for m in metas if m['meta_renovaciones']>0]
        if len(con_datos) >= 3:
            u3 = con_datos[-3:]
            rec_ren = round(max(m['meta_renovaciones'] for m in u3)*1.10)
            rec_nuevos = round(max(m['meta_nuevos'] for m in u3)*1.10)
            for m in metas:
                m['rec_renovaciones'] = rec_ren
                m['rec_nuevos'] = rec_nuevos
        return jsonify(metas)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/metas', methods=['POST'])
@login_required
def crear_meta():
    try:
        sh = get_sheet()
        ws = sh.worksheet('Metas')
        rows = ws.get_all_values()
        d = request.json
        mes = d.get('mes','')
        for i, row in enumerate(rows):
            if row and row[0] == mes:
                if d.get('modo') == 'real':
                    headers = rows[0]
                    if 'Real Clientes Nuevos' in headers:
                        ws.update_cell(i+1, headers.index('Real Clientes Nuevos')+1, d.get('real_nuevos',''))
                    if 'Real Renovaciones' in headers:
                        ws.update_cell(i+1, headers.index('Real Renovaciones')+1, d.get('real_renovaciones',''))
                    return jsonify({'ok':True,'action':'updated_real'})
                else:
                    return jsonify({'ok':False,'error':'Meta ya existe para este mes'}), 400
        ws.append_row([mes, d.get('meta_nuevos',0), '', d.get('meta_renovaciones',0), ''])
        return jsonify({'ok':True,'action':'created'})
    except Exception as e:
        return jsonify({'error':str(e)}), 500

@app.route('/api/config')
@login_required
def get_config():
    try:
        sh = get_sheet()
        rows = sheet_to_dicts(sh.worksheet('Configuración'))
        result = {}
        for r in rows:
            cat = r.get('Categoria','').strip()
            val = r.get('Valor','').strip()
            if cat and val:
                if cat not in result: result[cat] = []
                result[cat].append(val)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/config', methods=['POST'])
@login_required
def guardar_config():
    try:
        sh = get_sheet()
        ws = sh.worksheet('Configuración')
        d = request.json
        ws.append_row([d.get('categoria',''), d.get('valor','')])
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/config', methods=['DELETE'])
@login_required
def eliminar_config():
    try:
        sh = get_sheet()
        ws = sh.worksheet('Configuración')
        rows = ws.get_all_values()
        d = request.json
        cat = d.get('categoria',''); val = d.get('valor','')
        for i, row in enumerate(rows[1:], start=2):
            if row[0].strip()==cat and row[1].strip()==val:
                ws.delete_rows(i)
                return jsonify({'ok': True})
        return jsonify({'error': 'No encontrado'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_ads_client():
    config = {
        'developer_token': os.getenv('DEVELOPER_TOKEN'),
        'client_id': os.getenv('CLIENT_ID'),
        'client_secret': os.getenv('CLIENT_SECRET'),
        'refresh_token': os.getenv('REFRESH_TOKEN'),
        'login_customer_id': os.getenv('MCC_ID'),
        'use_proto_plus': True
    }
    path = '/tmp/gads_general.yaml'
    with open(path, 'w') as f:
        yaml.dump(config, f)
    return GoogleAdsClient.load_from_storage(path)

def get_date_range(periodo):
    hoy = date.today()
    if periodo == 'hoy': return str(hoy), str(hoy)
    elif periodo == 'ayer': ayer=hoy-timedelta(days=1); return str(ayer), str(ayer)
    elif periodo == 'semana': inicio=hoy-timedelta(days=hoy.weekday()); return str(inicio), str(hoy)
    elif periodo == 'mes_pasado':
        if hoy.month==1: inicio=date(hoy.year-1,12,1); fin=date(hoy.year-1,12,31)
        else: inicio=date(hoy.year,hoy.month-1,1); fin=date(hoy.year,hoy.month-1,calendar.monthrange(hoy.year,hoy.month-1)[1])
        return str(inicio), str(fin)
    else: inicio=date(hoy.year,hoy.month,1); return str(inicio), str(hoy)

@app.route('/api/googleads')
@login_required
def get_googleads():
    try:
        periodo = request.args.get('periodo', 'mes')
        fecha_ini, fecha_fin = get_date_range(periodo)
        sh = get_sheet()
        clientes = sheet_to_dicts(sh.worksheet('Clientes'))
        activos = [c for c in clientes if c.get('Estado','').strip().lower()!='perdido' and c.get('ID Google Ads','').strip()]
        if not activos: return jsonify([])
        ads_client = get_ads_client()
        ga_service = ads_client.get_service('GoogleAdsService')
        hoy30=date.today(); ini30=hoy30-timedelta(days=30)
        result = []
        for c in activos:
            gads_id = c.get('ID Google Ads','').strip().replace('-','')
            if not gads_id: continue
            try:
                q = f"SELECT metrics.impressions,metrics.clicks,metrics.ctr,metrics.average_cpc,metrics.cost_micros FROM campaign WHERE segments.date BETWEEN '{fecha_ini}' AND '{fecha_fin}'"
                imp=clics=costo=0
                for row in ga_service.search(customer_id=gads_id, query=q):
                    m=row.metrics; imp+=m.impressions; clics+=m.clicks; costo+=m.cost_micros
                costo_clp=round(costo/1_000_000)
                q30=f"SELECT metrics.cost_micros FROM campaign WHERE segments.date BETWEEN '{ini30}' AND '{hoy30}'"
                costo30=round(sum(r.metrics.cost_micros for r in ga_service.search(customer_id=gads_id,query=q30))/1_000_000)
                ctr=round((clics/imp*100) if imp>0 else 0,2)
                cpc=round((costo_clp/clics) if clics>0 else 0)
                monto=parse_int(c.get('Monto',0)); inv=parse_int(c.get('Inversión Ads',0))
                es_admin=c.get('Plan','')=='Administración'
                result.append({'id':c.get('ID',''),'nombre':c.get('Nombre',''),'plan':c.get('Plan',''),
                    'monto':monto,'inversion_ads':inv,'rentabilidad':monto-inv,'google_ads_id':gads_id,
                    'costo_ads':costo_clp,'impresiones':imp,'clics':clics,'ctr':ctr,'cpc':cpc,
                    'costo_30d':0 if es_admin else costo30,'alerta_inv':False if es_admin else costo30>inv})
            except Exception as ex:
                monto=parse_int(c.get('Monto',0)); inv=parse_int(c.get('Inversión Ads',0))
                result.append({'id':c.get('ID',''),'nombre':c.get('Nombre',''),'plan':c.get('Plan',''),
                    'monto':monto,'inversion_ads':inv,'rentabilidad':monto-inv,'google_ads_id':gads_id,
                    'costo_ads':0,'impresiones':0,'clics':0,'ctr':0,'cpc':0,'costo_30d':0,'alerta_inv':False,'error':str(ex)})
        return jsonify(result)
    except Exception as e:
        return jsonify({'error':str(e)}), 500

@app.route('/api/googleads/<gads_id>')
@login_required
def get_googleads_detalle(gads_id):
    try:
        periodo = request.args.get('periodo','mes')
        fecha_ini, fecha_fin = get_date_range(periodo)
        ads_client = get_ads_client()
        ga_service = ads_client.get_service('GoogleAdsService')
        query = f"""SELECT segments.date,campaign.name,metrics.impressions,metrics.clicks,
                   metrics.ctr,metrics.average_cpc,metrics.cost_micros,metrics.conversions,
                   metrics.search_impression_share,metrics.search_budget_lost_impression_share,
                   metrics.search_rank_lost_impression_share
                   FROM campaign WHERE segments.date BETWEEN '{fecha_ini}' AND '{fecha_fin}'
                   ORDER BY segments.date DESC"""
        rows = []
        for row in ga_service.search(customer_id=gads_id.replace('-',''), query=query):
            m=row.metrics
            rows.append({'fecha':row.segments.date,'campana':row.campaign.name,
                'impresiones':m.impressions,'clics':m.clicks,'ctr':round(m.ctr*100,2),
                'cpc':round(m.average_cpc/1_000_000,0),'costo':round(m.cost_micros/1_000_000,0),
                'conversiones':round(m.conversions,1),
                'is_ganado':round((m.search_impression_share or 0)*100,1),
                'is_presupuesto':round((m.search_budget_lost_impression_share or 0)*100,1),
                'is_ranking':round((m.search_rank_lost_impression_share or 0)*100,1)})
        return jsonify(rows)
    except Exception as e:
        return jsonify({'error':str(e)}), 500

@app.route('/api/googleads/<gads_id>/estructura')
@login_required
def get_googleads_estructura(gads_id):
    try:
        periodo = request.args.get('periodo', 'mes')
        fecha_ini, fecha_fin = get_date_range(periodo)
        ads_client = get_ads_client()
        ga_service = ads_client.get_service('GoogleAdsService')
        cid = gads_id.replace('-','')
        q_kw = "SELECT ad_group_criterion.keyword.text FROM ad_group_criterion WHERE ad_group_criterion.type = 'KEYWORD' AND ad_group_criterion.status = 'ENABLED'"
        kw_count = sum(1 for _ in ga_service.search(customer_id=cid, query=q_kw))
        q_ag = f"SELECT ad_group.id,metrics.impressions FROM ad_group WHERE segments.date BETWEEN '{fecha_ini}' AND '{fecha_fin}' AND metrics.impressions > 0"
        ag_count = sum(1 for _ in ga_service.search(customer_id=cid, query=q_ag))
        q_ad = f"SELECT ad_group_ad.ad.id,metrics.impressions FROM ad_group_ad WHERE segments.date BETWEEN '{fecha_ini}' AND '{fecha_fin}' AND metrics.impressions > 0"
        ad_count = sum(1 for _ in ga_service.search(customer_id=cid, query=q_ad))
        return jsonify({'keywords': kw_count, 'grupos': ag_count, 'anuncios': ad_count})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print('\n🚀 Vendermas General corriendo en http://localhost:5001\n')
    app.run(debug=True, port=5001)
