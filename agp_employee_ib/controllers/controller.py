import re
import json
import odoo
import requests
import time
import logging
from odoo import http, _
from odoo.http import request
from odoo.addons.web.controllers.utils import ensure_db, _get_login_redirect_url
from odoo.exceptions import AccessDenied
from datetime import datetime, time as dt_time, timedelta

_logger = logging.getLogger(__name__)

SIGN_UP_REQUEST_PARAMS = {'db', 'login', 'debug', 'token', 'message', 'error', 'scope', 'mode',
                          'redirect', 'redirect_hostname', 'email', 'name', 'partner_id',
                          'password', 'confirm_password', 'city', 'country_id', 'lang', 'signup_email'}
LOGIN_SUCCESSFUL_PARAMS = set()


class Home(http.Controller):

    def _login_redirect(self, uid, redirect=None):
        return _get_login_redirect_url(uid, redirect)

    @http.route('/web/login', type='http', auth="none")
    def web_login(self, redirect=None, **kw):
        ensure_db()
        request.params['login_success'] = False
        client_ip = request.httprequest.remote_addr

        if request.httprequest.method == 'GET' and redirect and request.session.uid:
            return request.redirect(redirect)

        if request.env.uid is None:
            if request.session.uid is None:
                request.env["ir.http"]._auth_method_public()
            else:
                request.update_env(user=request.session.uid)

        values = {k: v for k, v in request.params.items() if k in SIGN_UP_REQUEST_PARAMS}

        try:
            values['databases'] = http.db_list()
        except odoo.exceptions.AccessDenied:
            values['databases'] = None

        if request.httprequest.method == 'POST':
            if not self._is_login_attempt_allowed(client_ip):
                values['error'] = _("Too many failed login attempts. Please wait and try again later.")
                _logger.warning(f"Brute-force attempt detected from {client_ip}. Login temporarily locked.")
                return request.render('web.login', values)

            try:
                uid = request.session.authenticate(request.db, request.params['login'], request.params['password'])
                request.params['login_success'] = True

                self._reset_login_attempts(client_ip)

                _logger.info(f"User {request.params['login']} logged in successfully from {client_ip}")

                redirect_log = request.env['redirect.url.log'].sudo().search([
                    ('user_id', '=', request.session.uid),
                    ('is_processed', '=', False)
                ], limit=1, order="timestamp desc")

                if redirect_log:
                    target_url = redirect_log.target_url
                    redirect_log.sudo().write({'is_processed': True})
                    return request.redirect(self._sanitize_redirect_url(target_url))

                return request.redirect(self._login_redirect(uid, redirect=redirect))
            except AccessDenied as e:
                self._increment_login_attempts(client_ip)

                _logger.warning(f"Failed login attempt for {request.params['login']} from {client_ip}")

                if e.args == AccessDenied().args:
                    values['error'] = _("Wrong login/password")
                else:
                    values['error'] = e.args[0]
        else:
            if 'error' in request.params and request.params.get('error') == 'access':
                values['error'] = _('Only employees can access this database. Please contact the administrator.')

        if 'login' not in values and request.session.get('auth_login'):
            values['login'] = request.session.get('auth_login')

        if not odoo.tools.config['list_db']:
            values['disable_database_manager'] = True

        response = request.render('web.login', values)
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['Content-Security-Policy'] = "frame-ancestors 'self'"
        return response

    def _sanitize_redirect_url(self, target_url):
        allowed_host = request.env['ir.config_parameter'].sudo().get_param('web.base.url', request.httprequest.host)
        if re.match(rf"^https?://({allowed_host}|localhost)", target_url):
            return target_url
        return '/'

    def _is_login_attempt_allowed(self, client_ip):
        param = request.env['ir.config_parameter'].sudo()

        max_attempts = int(param.get_param('auth.max_login_attempts', default=5))
        lockout_time = int(param.get_param('auth.lockout_time', default=300))

        now = time.time()
        attempts = request.session.get(f'login_attempts_{client_ip}', 0)

        if isinstance(attempts, list):
            _logger.warning(f"Incorrect data type detected in session! Resetting login attempts for {client_ip}.")
            self._reset_login_attempts(client_ip)
            attempts = 0

        attempts = int(attempts)

        _logger.info(f"🔍 Login attempts: {attempts} | Max allowed: {max_attempts} | Lockout time: {lockout_time} | IP: {client_ip}")

        if attempts >= max_attempts:
            last_attempt_time = request.session.get(f'last_attempt_{client_ip}', now)
            if now - last_attempt_time < lockout_time:
                _logger.warning(f"Brute-force protection activated for {client_ip}. Lockout in effect.")
                return False
            else:
                self._reset_login_attempts(client_ip)

        return True

    def _increment_login_attempts(self, client_ip):
        now = time.time()
        attempts = request.session.get(f'login_attempts_{client_ip}', 0)

        if isinstance(attempts, list):
            _logger.warning(f"Incorrect data type detected in session! Resetting login attempts for {client_ip}.")
            self._reset_login_attempts(client_ip)
            attempts = 0

        attempts = int(attempts) + 1
        request.session[f'login_attempts_{client_ip}'] = attempts
        request.session[f'last_attempt_{client_ip}'] = now

        _logger.info(f"Incrementing login attempts for {client_ip}: Now {attempts}")

    def _reset_login_attempts(self, client_ip):
        request.session[f'login_attempts_{client_ip}'] = 0
        request.session[f'last_attempt_{client_ip}'] = 0
        _logger.info(f"Reset login attempts for {client_ip}")


class HolidayController(http.Controller):

    @http.route('/agp_employee_ib/get_holiday_data', type='json', auth='user')
    def get_holiday_data(self):
        try:
            api_url = "https://dayoffapi.vercel.app/api"
            response = requests.get(api_url, timeout=10)
            response.raise_for_status()
            holidays = response.json()

            holiday_model = request.env['resource.calendar.leaves'].sudo()
            created_holidays = 0

            for holiday in holidays:
                holiday_date_from = datetime.strptime(holiday['tanggal'], '%Y-%m-%d')
                holiday_date_to = datetime.strptime(holiday['tanggal'], '%Y-%m-%d')
                holiday_datetime_from = datetime.combine(holiday_date_from, dt_time.min) - timedelta(hours=7)
                holiday_datetime_to = datetime.combine(holiday_date_to, dt_time.max) - timedelta(hours=7)

                existing_holiday = holiday_model.search([
                    ('name', '=', holiday['keterangan']),
                    ('date_from', '=', holiday_datetime_from),
                    ('date_to', '=', holiday_datetime_to),
                ], limit=1)

                if not existing_holiday:
                    holiday_model.create({
                        'name': holiday['keterangan'],
                        'date_from': holiday_datetime_from,
                        'date_to': holiday_datetime_to,
                        'is_cuti': holiday.get('is_cuti', False)
                    })
                    created_holidays += 1

            return {
                'success': True,
                'message': f'{created_holidays} new holidays added successfully!',
            }

        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'message': f"Request error: {str(e)}"
            }
        except Exception as e:
            return {
                'success': False,
                'message': f"Error: {str(e)}"
            }


class EmployeeAPIController(http.Controller):

    @http.route('/api/employees', type='http', auth='user', methods=['GET'], csrf=False)
    def get_employees(self, **kwargs):
        employees = request.env['hr.employee'].sudo().search([])
        result = []
        for emp in employees:
            nip_value = ""
            if emp.employment_type == 'organik':
                nip_value = emp.nip_organik or ""
            elif emp.employment_type == 'pkwt':
                nip_value = emp.nip_pkwt or ""

            result.append({
                'id': emp.id,
                'name': emp.name,
                'job_title': emp.job_id.name if emp.job_id else "",
                'work_email': emp.work_email or "",
                'nip': nip_value,
                'jabatan': emp.keterangan_jabatan_id.name,
                'unit': emp.hr_employee_unit_id.name,
                'lokasi': emp.hr_branch_id.name,
            })

        return request.make_response(
            json.dumps({"status": "success", "employees": result}),
            headers=[('Content-Type', 'application/json')]
        )

    @http.route('/redirect_to_simkp_post', type='http', auth='user', methods=['GET'], csrf=False)
    def redirect_to_simkp_post(self, **kwargs):
        employee_id = kwargs.get('employee_id')
        if employee_id:
            try:
                employee_id = int(employee_id)
            except ValueError:
                employee_id = False

        employee = request.env['hr.employee'].sudo().browse(employee_id)
        if employee and employee.user_id:
            user_login = employee.user_id.login
        else:
            user_login = request.env.user.login

        target_url = 'http://simkp.adhigunaputera.co.id/simkp/areaodoo.php'
        html = f"""
            <html>
              <head>
                <meta charset="utf-8"/>
                <title>Redirecting...</title>
              </head>
              <body onload="document.getElementById('post_form').submit();">
                <form id="post_form" action="{target_url}" method="POST">
                  <input type="hidden" name="odoo" value="{user_login}" />
                </form>
                <p>Redirecting... jika tidak segera ter-redirect, <a href="#" onclick="document.getElementById('post_form').submit(); return false;">klik disini</a>.</p>
              </body>
            </html>
            """
        return request.make_response(html, headers=[('Content-Type', 'text/html')])