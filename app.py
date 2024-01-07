import os
import csv
import datetime
from kivy.app import App
from kivy.uix.image import Image
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.slider import Slider
from kivy.uix.spinner import Spinner
from kivy.graphics import Color, Line, Rectangle
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from PIL import Image as PILImage
from kivy.uix.recycleview import RecycleView
from kivy.uix.textinput import TextInput
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.togglebutton import ToggleButtonBehavior
import time
import random
import string
from kivy.core.window import Window

Window.fullscreen = True


class DrawWidget(Widget):
    def __init__(self, **kwargs):
        super(DrawWidget, self).__init__(**kwargs)
        self.line_width = 2
        self.draw_color = (1, 0, 0)  # Red color
        self.mode = 'neutral'
        self.drawn_points_with_sizes = []  # 座標とサイズのペアのリスト
        self.last_touch_pos = None

    def on_touch_down(self, touch):
        if self.parent.collide_point(*touch.pos):
            self.last_touch_pos = touch.pos
            self.update_drawing(touch)

    def on_touch_move(self, touch):
        if self.parent.collide_point(*touch.pos) and self.last_touch_pos:
            self.update_drawing(touch)

    def update_drawing(self, touch):
        if self.mode == 'draw':
            self.add_line(self.last_touch_pos, touch.pos)
        elif self.mode == 'erase':
            self.erase_points(touch)
        self.last_touch_pos = touch.pos

    def add_line(self, start, end):
        steps = max(abs(start[0] - end[0]), abs(start[1] - end[1]))
        if steps == 0:
            # タッチ開始点と終了点が同じ場合は、点を直接追加
            self.drawn_points_with_sizes.append((start[0], start[1], self.line_width))
        else:
            for i in range(int(steps) + 1):
                t = i / steps
                x = int(start[0] * (1 - t) + end[0] * t)
                y = int(start[1] * (1 - t) + end[1] * t)
                point_size_pair = (x, y, self.line_width)
                self.drawn_points_with_sizes.append(point_size_pair)
        self.redraw_lines()

    def erase_points(self, touch):
        erase_radius = self.line_width * 2
        erase_touch_pos = touch.pos
        points_to_keep = []
        for x, y, size in self.drawn_points_with_sizes:
            if not self.is_point_in_radius((x, y), erase_touch_pos, erase_radius):
                points_to_keep.append((x, y, size))
        self.drawn_points_with_sizes = points_to_keep
        self.redraw_lines()

    def is_point_in_radius(self, point, center, radius):
        return (point[0] - center[0])**2 + (point[1] - center[1])**2 < radius**2

    def redraw_lines(self):
        self.canvas.clear()
        with self.canvas:
            Color(*self.draw_color)
            for point in self.drawn_points_with_sizes:
                x, y, size = point
                Line(points=[x, y, x + 1, y + 1], width=size)

    def set_line_width(self, line_width):
        self.line_width = line_width

    def set_draw_mode(self):
        self.mode = 'draw'

    def set_erase_mode(self):
        self.mode = 'erase'

    def set_neutral_mode(self):
        self.mode = 'neutral'

    def clear_canvas(self):
        self.canvas.clear()
        self.lines = []

    def save_drawing(self, file_path):
        self.export_to_png(file_path)
    
    def get_drawn_points(self):
        return [(x, y) for x, y, _ in self.drawn_points_with_sizes]
    
    def clear_canvas(self):
        self.canvas.clear()
        self.lines = []
        self.drawn_points_with_sizes = []  # 座標とサイズのリストもクリア

    def export_with_transparent_background(self, file_path):
        display_area_size = self.parent.norm_image_size
        display_area_pos = self.parent.center

        self.size = display_area_size
        self.center = display_area_pos

        with self.canvas:
            Color(0, 0, 0, 0)  # 透明な背景色を設定
            self.rect = Rectangle(size=self.size, pos=self.pos)

        self.export_to_png(file_path)  # PNGとしてエクスポート

        # キャンバスから透明な背景を削除
        self.canvas.remove(self.rect)

class RadioButton(ToggleButton):
    def __init__(self, **kwargs):
        super(RadioButton, self).__init__(**kwargs)


class ImageViewerApp(App):
    selected_user_id = None
    selected_user_name = None
    user_data = []
    filtered_users = []

    def build(self):
        self.draw_widget = DrawWidget()
        self.draw_widget.set_neutral_mode()

        # ユーザーのホームディレクトリを取得
        home_directory = os.path.expanduser('~')
        user_csv_path = os.path.join(home_directory, 'Interpretation_experiment', 'user.csv')
        self.user_data = self.read_user_csv(user_csv_path)

        self.layout = BoxLayout(orientation='vertical', padding=[20, 40, 20, 40], spacing=20)

        self.description_label = Label(
        text="""Please write your first name in the textbox and select your session type.
        If this is your first session (not assisted), choose session type A;
        if it is your second session (assisted), choose session type B.""",
        font_size='20sp',
        size_hint_y=None,
        height=90,
        halign='center',  # Horizontal alignment
        valign='middle'
        )

        # Bind the label's text_size to the layout's width
        self.description_label.bind(width=lambda instance, value: setattr(instance, 'text_size', (value, None)))


        self.layout.add_widget(self.description_label)

        # ユーザー検索用のTextInputを追加
        self.user_search_input = TextInput(size_hint_y=None, height=60, hint_text='write your name', font_size='20sp')
        self.user_search_input.bind(text=self.on_user_search)

        # 検索結果を表示するためのSpinnerを追加
        self.user_search_spinner = Spinner(size_hint_y=None, height=40, text='Click here and choose your name after write your first name above', font_size='20sp')
        self.user_search_spinner.bind(text=self.on_spinner_select)
        self.layout.add_widget(self.user_search_input)
        self.layout.add_widget(self.user_search_spinner)

        # セッションタイプ選択用のドロップダウンとスタートボタンを追加
        self.session_type_dropdown = Spinner(size_hint_y=None, text='Select Session Type', height=40, values=['A', 'B'], font_size='20sp')
        self.session_type_dropdown.bind(text=self.on_session_type_dropdown_select)
        
        self.start_button = Button(size_hint_y=None, text='Start Session', height=30, on_press=self.start_session, font_size='20sp')
        self.layout.add_widget(self.session_type_dropdown)
        self.layout.add_widget(self.start_button)

        return self.layout

    def on_session_type_dropdown_select(self, instance, text):
        self.session_type = text
        # セッションタイプに基づいてユーザーリストをフィルタリング
        self.filtered_users = [row['name'] for row in self.user_data]
        self.user_search_spinner.values = self.filtered_users

    def on_user_search(self, instance, text):
        # ユーザー検索のテキストに基づいてユーザーリストをフィルタリング
        self.filtered_users = [row['name'] for row in self.user_data if text.lower() in row['name'].lower()]
        self.user_search_spinner.values = self.filtered_users

    def on_spinner_select(self, spinner, text):
        # Spinnerで選択されたユーザーを処理
        selected_user = next((user for user in self.user_data if user['name'] == text), None)
        if selected_user:
            self.selected_user_id = selected_user['user_id']
            self.selected_user_name = selected_user['name']
            print(f"Selected user: {self.selected_user_name} with ID {self.selected_user_id}")

    def read_user_csv(self, csv_file):
        user_data = []
        if os.path.exists(csv_file):
            with open(csv_file, 'r', newline='') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    user_data.append(row)
        return user_data


    def start_session(self, instance):
        user_id = self.selected_user_id

        self.layout.clear_widgets()
        # レイアウトの外縁に余白を追加
        self.layout.padding = [5, 5, 5, 5]
        self.layout.spacing = 18

        home_directory = os.path.expanduser('~')
        if self.session_type == 'A':
            self.image_folder = os.path.join(home_directory, 'Interpretation_experiment', 'dataset_A')
        elif self.session_type == 'B':
            self.image_folder = os.path.join(home_directory, 'Interpretation_experiment', 'dataset_B')

        self.images = [os.path.join(self.image_folder, f) for f in os.listdir(self.image_folder) if f.lower().endswith('.jpg')]
        self.current_image_index = 0

        self.image_widget = Image(source=self.images[self.current_image_index], allow_stretch=True, keep_ratio=True)
        self.image_widget.size_hint = (1, 1)

        self.draw_widget = DrawWidget()
        self.image_widget.add_widget(self.draw_widget)
        
        self.draw_widget.size = self.image_widget.norm_image_size
        self.draw_widget.pos = self.image_widget.pos
        

        # ボタンを作成し、レイアウトに追加
        # モードボタン用の水平BoxLayoutを作成
        mode_button_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint=(1, 0.05))

        # ラジオボタンを作成し、レイアウトに追加
        self.draw_mode_button = RadioButton(size_hint_y=None, height=15, text='Draw Mode', group='mode', on_press=lambda instance: self.draw_widget.set_draw_mode(), font_size='18sp', size_hint=(1, 1))
        self.erase_mode_button = RadioButton(size_hint_y=None, height=15, text='Erase Mode', group='mode', on_press=lambda instance: self.draw_widget.set_erase_mode(), font_size='18sp', size_hint=(1, 1))
        self.neutral_mode_button = RadioButton(size_hint_y=None, height=15, text='Neutral Mode', group='mode', on_press=lambda instance: self.draw_widget.set_neutral_mode(), font_size='18sp', size_hint=(1, 1))

        mode_button_layout.add_widget(self.draw_mode_button)
        mode_button_layout.add_widget(self.erase_mode_button)
        mode_button_layout.add_widget(self.neutral_mode_button)

        # モードボタンのレイアウトをメインレイアウトに追加

        self.next_button = Button(size_hint_y=None, height=20,text='Next Image', on_press=self.next_image, size_hint=(1, 0.08), font_size='20sp')
        self.line_width_slider = Slider(min=1, max=10, value=5, size_hint=(1, 0.04))
        self.line_width_slider.bind(value=self.on_line_width_change)

        self.line_width_label = Label(text='Marker size: 5', size_hint=(1, 0.02), font_size='18sp')

        self.confidence_slider = Slider(min=0, max=100, value=50, step=1, size_hint=(1, 0.04))
        self.confidence_label = Label(text='Confidence: 50', size_hint=(1, 0.02), font_size='18sp')

        # Create radio buttons for True and False option
        radio_button_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint=(1, 0.05))

        # Create radio buttons for True and False options
        self.true_radio_button = RadioButton(state='normal',size_hint_y=None, height=30, text='True', group='response', font_size='20sp')
        self.false_radio_button = RadioButton(state='normal',size_hint_y=None, height=30, text='False', group='response', font_size='20sp')

        self.radio_button_label = Label(text='Abnormal ?', size_hint=(1, 0.05), font_size='20sp')

        # Add radio buttons to the layout
        radio_button_layout.add_widget(self.true_radio_button)
        radio_button_layout.add_widget(self.false_radio_button)



        # 他のウィジェットをメインレイアウトに追加
        self.layout.add_widget(self.line_width_label)
        self.layout.add_widget(self.line_width_slider)
        self.layout.add_widget(mode_button_layout)

        self.layout.add_widget(self.image_widget)
        # ラジオボタンのレイアウトをメインレイアウトに追加
        self.layout.add_widget(self.radio_button_label)
        self.layout.add_widget(radio_button_layout)

        self.layout.add_widget(self.confidence_label)
        self.layout.add_widget(self.confidence_slider)

        self.layout.add_widget(self.next_button)

        self.start_time = datetime.datetime.now()
        self.reading_time = 0
        self.user_data = []
        self.page_start_time = datetime.datetime.now()

        self.confidence_slider.bind(value=self.on_slider_value_change)
        self.line_width_slider.bind(value=self.on_line_width_value_change)

    def on_slider_value_change(self, instance, value):
        self.confidence_label.text = f'Confidence: {int(value)}'

    def on_line_width_value_change(self, instance, value):
        self.line_width_label.text = f'Marker size: {int(value)}'
    
    def get_red_points(self, image_path):
        # 画像を読み込む
        image = PILImage.open(image_path)
        pixels = image.load()

        # 画像のサイズを取得
        width, height = image.size

        # 赤色のピクセルを探す
        red_points = []
        for x in range(width):
            for y in range(height):
                r, g, b, a = pixels[x, y]
                if r == 255 and g == 0 and b == 0:
                    red_points.append((x, y))
        return red_points


    def next_image(self, instance):
        current_click_time = time.time()
        if current_click_time - self.last_click_time < 0.3: 
            elapsed_time = (datetime.datetime.now() - self.page_start_time).total_seconds()
            self.page_start_time = datetime.datetime.now()

            user_id = self.selected_user_id
            self.session_id = self.generate_session_id(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), self.selected_user_id)
            
            confidence = int(self.confidence_slider.value)
            conducted_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            image_name = os.path.splitext(os.path.basename(self.images[self.current_image_index]))[0]

            self.save_current_image()

            # True/Falseの値を取得
            abnormal_response = 'True' if self.true_radio_button.state == 'down' else 'False'

            # 画像パスを取得
            # save_folderの定義
            home_directory = os.path.expanduser('~')
            save_folder = os.path.join(home_directory, 'Interpretation_experiment', 'read_images', f'{self.selected_user_id}-{self.session_type}')
            image_path = os.path.join(save_folder, image_name + '_read.png')

            # 赤色の座標を取得
            red_points = self.get_red_points(image_path)
            red_points_str = ';'.join([f'({x},{y})' for x, y in red_points])

            # user_dataに必要なデータを追加する
            self.user_data.append([
                self.session_id, user_id, self.session_type, confidence, 
                round(elapsed_time, 2), conducted_time, image_name, 
                abnormal_response, red_points_str
            ])
            

            self.true_radio_button.state = 'normal'
            self.false_radio_button.state = 'normal'

            # 次の画像に進む前にマーカー情報をクリア
            self.draw_widget.clear_canvas()

            self.current_image_index += 1
            if self.current_image_index < len(self.images):
                self.image_widget.source = self.images[self.current_image_index]
                self.confidence_slider.value = 50
                self.confidence_label.text = 'Confidence: 50'
            else:
                # すべてのデータをsave_data_to_csvで保存する
                self.save_data_to_csv()
                self.stop()
        self.last_click_time = current_click_time

    def __init__(self, **kwargs):
        super(ImageViewerApp, self).__init__(**kwargs)
        self.last_click_time = 0  # ここで last_click_time を初期化
    
    def generate_session_id(self, conducted_time, user_id):
        random_string = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
        return f"{conducted_time.replace(':', '').replace('-', '').replace(' ', '')}_{random_string}_{user_id}"


    def save_data_to_csv(self):
        home_directory = os.path.expanduser('~')
        csv_file = os.path.join(home_directory, 'Interpretation_experiment', 'performance.csv')
        file_exists = os.path.exists(csv_file)

        with open(csv_file, 'a', newline='') as file:
            writer = csv.writer(file)
            if not file_exists:
                writer.writerow(['session_id', 'user_id', 'session_type', 'confidence', 'reading_time', 'conducted_time', 'image_name', 'abnormal', 'drawm_points'])
            
            for data_row in self.user_data:
                writer.writerow(data_row)


    def on_line_width_change(self, instance, value):
        self.draw_widget.set_line_width(value)

    def save_current_image(self):
        if self.selected_user_id and self.session_type:
            home_directory = os.path.expanduser('~')
            save_folder = os.path.join(home_directory, 'Interpretation_experiment', 'read_images', f'{self.selected_user_id}-{self.session_type}')
            
            if not os.path.exists(save_folder):
                os.makedirs(save_folder)
            image_name = os.path.basename(self.images[self.current_image_index]).replace('.jpg', '_read.png')
            save_path = os.path.join(save_folder, image_name)

            # Export the current drawing with a transparent background
            temp_drawing_path = os.path.join(save_folder, 'temp_drawing.png')
            self.draw_widget.export_with_transparent_background(temp_drawing_path)

            # Load the original image and the drawing
            original_image = PILImage.open(self.images[self.current_image_index]).convert('RGBA')
            drawing = PILImage.open(temp_drawing_path).convert('RGBA')

            # Resize the drawing to match the original image size
            drawing_resized = drawing.resize(original_image.size, PILImage.Resampling.LANCZOS)

            # Calculate the scale ratio
            scale_x = original_image.width / self.draw_widget.width
            scale_y = original_image.height / self.draw_widget.height

            # Scale the drawn points and store them in a class attribute
            self.scaled_drawn_points = [(x * scale_x, y * scale_y) for x, y in self.draw_widget.get_drawn_points()]

            # Composite the drawing onto the original image
            combined = PILImage.alpha_composite(original_image, drawing_resized)
            combined.save(save_path, 'PNG')

            # Remove the temporary drawing file
            os.remove(temp_drawing_path)


if __name__ == '__main__':
    ImageViewerApp().run()