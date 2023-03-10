from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
import time
import re
from datetime import datetime, time as timed, timedelta
import pytz
import csv
from icalendar import Calendar, Event
import os
from plyer import notification


class UOC:
    PAGE_LOGIN_UOC = "https://cv.uoc.edu/auth?campus-nplincampus"
    PAGE_CLASSROOM_UOC = "https://campus.uoc.edu/webapps/aulaca/classroom/Classroom.action?"

    # https://chromedriver.chromium.org/downloads

    def __init__(self, config):
        # Init variables
        self.config = config
        self.error = False
        self.errorMessage = ""
        self.campusSessionId = ""
        # Check config file
        self.check_config_file()
        self.driver = None
        # If not error, set variables
        if not self.error:
            self.username = config["username"]
            self.password = config["password"]
            self.classroomIds = config["classroomIds"]
            self.classroomId_colors = self.get_classroomId_colors()
            self.classroomId_names = self.get_classroomId_names()
            self.classroomId_subjectIds = self.get_classroomId_subjectIds()
            # configure options for chrome (run in background & not use GPU)
            # chrome_options = Options()
            # chrome_options.add_argument('--headless')
            # chrome_options.add_argument('--disable-gpu')
            self.driver = webdriver.Chrome(executable_path=self.config["path_executable_chromedriver"])
            # init timeline & messages
            self.timeline = dict()
            self.messages = dict()

    def check_config_file(self):
        if "username" in self.config and "password" in self.config and "classroomIds" in self.config:
            if "classroomId_names" not in self.config or\
                    "classroomId_subjectIds" not in self.config or\
                    "classroomId_colors" not in self.config:
                self.error = True
                self.errorMessage = "Some parameter (classroomId_names, classroomId_colors and/or " \
                                    "classroomId_subjectIds) not founded in config file!"
            else:
                len1 = len(self.config["classroomId_names"])
                len2 = len(self.config["classroomId_colors"])
                len3 = len(self.config["classroomId_subjectIds"])
                if len1 != len2 or len2 != len3:
                    self.error = True
                    self.errorMessage = "Some parameter (classroomId_names, classroomId_colors and/or " \
                                        "classroomId_subjectIds) with different length in config file!"
                else:
                    if "path_executable_chromedriver" in self.config and os.path.exists(
                            self.config["path_executable_chromedriver"]):
                        self.error = False
                    else:
                        self.error = True
                        self.errorMessage = "Chromedriver path not found!"

        else:
            self.error = True
            self.errorMessage = "Some parameter (username, password and/or classroomIds) not founded in config file!"

    def get_name(self, classroomId):
        if classroomId in self.config["classroomId_names"]:
            return self.config["classroomId_names"][classroomId]
        else:
            return ""

    def get_subjectId(self, classroomId):
        if classroomId in self.config["classroomId_subjectIds"]:
            return self.config["classroomId_subjectIds"][classroomId]
        else:
            return ""

    def get_color(self, classroomId):
        if classroomId in self.config["classroomId_colors"]:
            return self.config["classroomId_colors"][classroomId]
        else:
            return ""

    def get_classroomId_names(self):
        classroomId_names = dict()
        for classroomId in self.classroomIds:
            classroomId_names[classroomId] = self.get_name(classroomId)
        return classroomId_names

    def get_classroomId_subjectIds(self):
        classroomId_subjectIds = dict()
        for classroomId in self.classroomIds:
            classroomId_subjectIds[classroomId] = self.get_subjectId(classroomId)
        return classroomId_subjectIds

    def get_classroomId_colors(self):
        classroomId_colors = dict()
        for classroomId in self.classroomIds:
            classroomId_colors[classroomId] = self.get_color(classroomId)
        return classroomId_colors

    def get_cookie(self, name):
        cookies = self.driver.get_cookies()
        value = ""

        for cookie in cookies:
            if cookie["name"] == name:
                value = cookie["value"]

        return value

    def login_UOC(self):
        try:
            self.driver.get(self.PAGE_LOGIN_UOC)
            # Esperar a que se cargue la página de inicio de sesión
            username_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "j_username")))
            password_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "j_password")))

            # Ingresar las credenciales de inicio de sesión y enviar el formulario
            username_field.send_keys(self.username)
            password_field.send_keys(self.password)
            password_field.send_keys(Keys.RETURN)

            self.campusSessionId = self.get_cookie("campusSessionId")
        except Exception as e:
            self.error = True
            self.errorMessage = "Error in login: " + str(e)

    def get_data_url(self, subjectId, classroomId):
        url = self.PAGE_CLASSROOM_UOC + f's={self.campusSessionId}' \
                                        f'&subjectId={subjectId}' \
                                        f'&classroomId={classroomId}&eventId=&javascriptDisabled=true'
        return url

    def get_difference_days(self, date1, date2):
        format = "%d/%m/%Y"
        date1 = datetime.strptime(date1, format)
        date2 = datetime.strptime(date2, format)
        difference = date2 - date1

        return difference.days

    def load_data_page(self, data_url):
        self.driver.get(data_url)
        # Esperar a que se cargue el contenido dinámico
        wait = WebDriverWait(self.driver, 10)
        wait.until(EC.presence_of_element_located((By.ID, 'container')))
        # extra time 3s
        time.sleep(3)

    def get_messages(self):
        messages = dict()
        for classroomId in self.classroomIds:
            classroom_name = self.classroomId_names[classroomId]
            if classroomId in self.classroomId_subjectIds.keys():
                subjectId = self.classroomId_subjectIds[classroomId]
                data_url = self.get_data_url(subjectId, classroomId)
                self.load_data_page(data_url)
                # get messages
                a_elements = self.driver.find_elements(By.CSS_SELECTOR, ".marcadors.LaunchesOWin")
                nuevos = False
                message_title = f"Messages in {classroom_name}:"
                for a_element in a_elements:
                    link = a_element.get_attribute("href")
                    nombre = a_element.get_attribute("data-bocamoll-object-description")
                    span_elements = a_element.find_elements(By.CSS_SELECTOR, ".new")
                    mensajes_nuevos = 0
                    mensajes_todos = 0
                    if len(span_elements) == 1:
                        mensajes_nuevos = span_elements[0].text
                    span_elements = a_element.find_elements(By.CSS_SELECTOR, ".all")
                    if len(span_elements) == 1:
                        mensajes_todos = span_elements[0].text
                    # save information in dict
                    if classroomId not in messages:
                        messages[classroomId] = list()
                    messages[classroomId].append([nombre, link, mensajes_nuevos, mensajes_todos])
                    if int(mensajes_nuevos) > 0:
                        message_content = f"{nombre}: {mensajes_nuevos} of {mensajes_todos}"
                        nuevos = True
                        UOC.show_toast(message_title, message_content)
                if not nuevos:
                    message_content = "No new messages!"
                print(message_title)
                print(message_content)
        self.messages = messages

    @staticmethod
    def show_toast(title, content, duration=10):
        notification.notify(
            title=title,
            message=content,
            app_name='Timeline UOC',
            # app_icon=os.path.abspath('images/icon_uoc.png'),
            timeout=duration
        )

    def get_timeline(self):
        timelines = dict()
        date_today_spain = UOC.get_date_spain()
        for classroomId in self.classroomIds:
            classroom_name = self.classroomId_names[classroomId]
            if classroomId in self.classroomId_subjectIds.keys():
                subjectId = self.classroomId_subjectIds[classroomId]
                data_url = self.get_data_url(subjectId, classroomId)
                self.load_data_page(data_url)
                # get timeline
                divs = self.driver.find_elements(By.CLASS_NAME, "tl-placeholder")
                if len(divs) == 2:
                    # only in second div
                    try:
                        divs_inside = divs[1].find_elements(By.CLASS_NAME, "tl-line")
                        for div_inside in divs_inside:
                            h2_element = div_inside.find_element(By.TAG_NAME, "h2")
                            tipo = h2_element.text
                            if tipo != "":
                                a_elements = div_inside.find_elements(By.TAG_NAME, "a")
                                for a_element in a_elements:
                                    # Search inside each a element
                                    texto_entero = a_element.get_attribute("title")
                                    patron = r"\d{2}/\d{2}/\d{4}"
                                    fechas = re.findall(patron, texto_entero)
                                    # datetime.strptime(fecha, "%d/%m/%Y")
                                    lista_fechas = [fecha for fecha in fechas]
                                    if len(lista_fechas) == 2:
                                        texto = texto_entero.split(" Inicio:")[0]
                                        inicio = lista_fechas[0]
                                        entrega = lista_fechas[1]
                                        activity_url = a_element.get_attribute("href")
                                        a_class = a_element.get_attribute("class")
                                        activity_name = a_element.get_attribute("aria-label")
                                        activity_name = activity_name.split(". Inicio:")[0]
                                        completed = "completed" in a_class
                                        activity_id = a_element.get_attribute("data-id")
                                        dias_diferencia = self.get_difference_days(date_today_spain, entrega)

                                        # put into timeline variable
                                        timelines[activity_id] = {
                                            "inicio": inicio,
                                            "entrega": entrega,
                                            "activity_id": activity_id,
                                            "activity_url": activity_url,
                                            "activity_name": activity_name,
                                            "classroomId": classroomId,
                                            "classroom_name": classroom_name,
                                            "subjectId": subjectId,
                                            "classroom_url": data_url,
                                            "type": tipo,
                                            "completed": completed,
                                            "days": dias_diferencia
                                        }
                                    else:
                                        print("Error timeline: Not found dates")
                            else:
                                print("Error timeline: Not found type activity")
                    except Exception as err:
                        print("Error timeline: Some error extracting info")
                        print(err)
                        pass

        self.timeline = timelines

    def get_sorted_timeline(self, field_name):
        def convertir_fecha(fecha):
            return datetime.strptime(fecha, "%d/%m/%Y")

        field_type_date = ["inicio", "entrega"]
        if field_name in field_type_date:
            return sorted(self.timeline.items(), key=lambda x: convertir_fecha(x[1][field_name]))

        return sorted(self.timeline.items(), key=lambda x: x[1][field_name])

    @staticmethod
    def get_date_spain():
        timezone = "Europe/Madrid"
        now_utc = datetime.now(tz=pytz.utc)
        now_local = now_utc.astimezone(pytz.timezone(timezone))
        format = "%d/%m/%Y"
        now_local_str = now_local.strftime(format)

        return now_local_str

    @staticmethod
    def get_span_code(text, background_color, color="#000", link=""):
        get_span_code = ""
        if link != "":
            get_span_code = f'<a href="{link}" target="_blank">'
        get_span_code += f'<span class="badge" style="background-color: {background_color}; color: {color}">{text}</span>'
        if link != "":
            get_span_code += '</a>'

        return get_span_code

    def rgb_to_hex(r, g, b):
        return '#{:02x}{:02x}{:02x}'.format(r, g, b)

    def get_timeline_html(self, sorted_by="inicio", create_csv=False):
        self.get_timeline()
        elements_timeline = self.get_sorted_timeline(sorted_by)
        content_csv = list()
        table_html = '<table id="timeline">' \
                     '<tr>' \
                     '<th>Nombre actividad</th>' \
                     '<th>Asignatura</th>' \
                     '<th>Tipo</th>' \
                     '<th>Days reminder</th>' \
                     '<th>Inicio</th>' \
                     '<th>Final</th>' \
                     '<th>Completada</th>' \
                     '</tr>'

        for el in elements_timeline:
            classroomId = el[1]["classroomId"]
            classroom_name = el[1]["classroom_name"]
            classroom_url = el[1]["classroom_url"]
            type = el[1]["type"]
            days = el[1]["days"]
            inicio = el[1]["inicio"]
            entrega = el[1]["entrega"]
            completed = el[1]["completed"]
            activity_name = el[1]["activity_name"]
            activity_url = el[1]["activity_url"]
            activity_id = el[1]["activity_id"]
            days_for_activty = self.get_difference_days(inicio, entrega)
            # get codes
            days_code = '<label for="' + str(activity_id) + '_time">' + str(
                days) + '&nbsp;</label><progress id="' + str(activity_id) + '_time" value="' + str(
                days) + '" max="' + str(days_for_activty) + '"></progress>'
            activity_name_code = UOC.get_span_code(activity_name, background_color=self.get_color(classroomId),
                                                   link=activity_url)
            classroom_name_code = UOC.get_span_code(classroom_name, background_color=self.get_color(classroomId),
                                                    link=classroom_url)
            type_code = UOC.get_span_code(type, background_color=UOC.get_type_color(type), color="#FFF")
            completed_image = './images/ko.png'
            if completed:
                completed_image = './images/ok.png'
            completed_code = f'<img src="{completed_image}" border="0" width="24" />'
            table_html += f'<tr><td align="left">{activity_name_code}</td>' \
                          f'<td>{classroom_name_code}</td>' \
                          f'<td>{type_code}</td>' \
                          f'<td>{days_code}</td>' \
                          f'<td>{inicio}</td>' \
                          f'<td>{entrega}</td>' \
                          f'<td>{completed_code}</td></tr>'
            content_csv.append([activity_name, classroom_name, type, days, inicio, entrega, completed])
        if create_csv:
            # create csv & ical files
            UOC.create_csv(content_csv)
            UOC.create_ical()

        table_html += '</table>'
        html = '''<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="ie=edge">
    <title>My timeline UOC</title>
    <link rel="stylesheet" href="./style.css">
    <link rel="icon" href="./favicon.ico" type="image/x-icon">
  </head>
  <body>
  <h2>Timeline ''' + str(UOC.get_date_spain()) + '''</h2>''' + table_html + '''
  </body>
</html>'''
        # Create timeline html
        f = open("timeline.html", "w", encoding='UTF-8')
        f.write(html)
        f.close()
        print("Timeline html created!")

    @staticmethod
    def create_csv(content_csv):
        archivo_csv = open('timeline.csv', mode='w', newline='', encoding='UTF-8')
        # Crear el objeto writer para escribir los datos en el archivo CSV
        writer = csv.writer(archivo_csv, delimiter=',')
        # write header
        writer.writerow(["Activity name", "Classroom name", "Activity type", "Days", "Start", "End", "Completed"])
        for contenido in content_csv:
            writer.writerow(contenido)

        archivo_csv.close()
        print("Timeline csv created!")

    @staticmethod
    def create_ical():
        # Abrir el archivo CSV y leer los datos
        with open('timeline.csv', newline='', encoding='utf-8') as archivo_csv:
            lector_csv = csv.reader(archivo_csv, delimiter=',')
            datos = list(lector_csv)
            # quitamos linea cabecera
            datos = datos[1:]

        # Crear el objeto de calendario iCal
        calendario = Calendar()

        # Iterar sobre los datos y crear un evento para cada fila
        for fila in datos:
            evento = Event()

            # Configurar el nombre y la descripción del evento
            evento.add('summary', fila[1] + " -> " + fila[2])
            evento.add('description', fila[0] + " -> " + fila[3] + " days")

            # Convertir la fecha y la hora de inicio y fin a objetos datetime
            inicio = datetime.strptime(fila[4], '%d/%m/%Y')
            fin = datetime.strptime(fila[5], '%d/%m/%Y')

            # Establecer la hora de inicio del día y la hora final de 23:59:59
            inicio = datetime.combine(inicio.date(), timed.min)
            fin = datetime.combine(fin.date(), timed.max) - timedelta(microseconds=1)

            # Configurar la fecha y hora de inicio y fin del evento
            evento.add('dtstart', inicio)
            evento.add('dtend', fin)

            # Agregar el evento al calendario
            calendario.add_component(evento)

        # Escribir el calendario iCal a un archivo
        with open('timeline.ics', 'wb') as archivo_ical:
            archivo_ical.write(calendario.to_ical())

        print("Timeline ics created!")

    @staticmethod
    def get_type_color(type_color):
        # https://www.color-hex.com/
        type_color = type_color.lower()
        color = "#c8cdcd"  # default color (gray)
        if "no evaluable" in type_color:
            color = "#297630"  # green
        if "pec" in type_color:
            color = "#3d76da"  # blue
        if "práctica" in type_color:
            color = "#d20000"  # red

        return color

    def __del__(self):
        try:
            self.driver.quit()
        except ImportError:
            pass
