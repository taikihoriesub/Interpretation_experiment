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
from kivy.clock import Clock

pixel_size = 512.0

#描図ウィジェットの設定を行う
class DrawWidget(Widget):
    def __init__(self, **kwargs):
        super(DrawWidget, self).__init__(**kwargs)
        self.line_width = 0
        self.draw_color = (0, 1, 0)  # green color
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
    
    #モードに応じた描図の更新の機能
    def update_drawing(self, touch):
        if self.mode == 'draw':
            self.add_line(self.last_touch_pos, touch.pos)
        elif self.mode == 'erase':
            self.erase_points(touch)
        self.last_touch_pos = touch.pos
    
    #マーカーの機能
    def add_line(self, start, end):
        steps = max(abs(start[0] - end[0]), abs(start[1] - end[1]))
        if steps == 0:
            # タッチ開始点と終了点が同じ場合は、点を直接追加
            self.drawn_points_with_sizes.append((start[0], start[1], 2*self.line_width))
        else:
            for i in range(int(steps) + 1):
                t = i / steps
                x = int(start[0] * (1 - t) + end[0] * t)
                y = int(start[1] * (1 - t) + end[1] * t)
                marker_size = 2*self.line_width
                point_size_pair = (x, y, marker_size)
                self.drawn_points_with_sizes.append(point_size_pair)
        self.redraw_lines()

    #消しゴムの機能
    #マーカーで描図された点の集合から消しゴムの半径内の点の集合を取り除く形で実装
    def erase_points(self, touch):
        erase_radius = self.line_width * 2
        erase_touch_pos = touch.pos
        points_to_keep = []
        for x, y, size in self.drawn_points_with_sizes:
            if not self.is_point_in_radius((x, y), erase_touch_pos, erase_radius):
                points_to_keep.append((x, y, size))
        self.drawn_points_with_sizes = points_to_keep
        self.redraw_lines()

    #領域内のマーカーの点を探して消す
    def is_point_in_radius(self, point, center, radius):
        return (point[0] - center[0])**2 + (point[1] - center[1])**2 < radius**2

    #マーカーで描図された点の集合から消しゴムの半径内の点の集合を可視化する
    def redraw_lines(self):
        self.canvas.clear()
        with self.canvas:
            Color(*self.draw_color)
            for point in self.drawn_points_with_sizes:
                x, y, size = point
                Line(points=[x, y, x + 1, y + 1], width=size)

    #マーカーや消しゴムのサイズを設定する
    def set_line_width(self, value):
        self.line_width = int(value)
    
    #モードボタンの設定
    def set_draw_mode(self):
        self.mode = 'draw'

    def set_erase_mode(self):
        self.mode = 'erase'

    def set_neutral_mode(self):
        self.mode = 'neutral'
    
    def get_drawn_points(self):
        return [(x, y, size) for x, y, size in self.drawn_points_with_sizes]
    
    #全消し機能の実装
    def clear_canvas(self):
        self.canvas.clear()
        self.mode = 'neutral'
        self.lines = []
        self.drawn_points_with_sizes = []  # 座標とサイズのリストもクリア
    
    #表示画面上でのマーカーの位置データについてピクセルデータへの変換を行う
    def normalize_point(self, x, y, size):    
        # 画像表示エリアのサイズを取得
        image_width, image_height = self.parent.norm_image_size
        image_x, image_y = self.parent.center_x - image_width / 2, self.parent.center_y - image_height / 2
        
        # 座標を正規化
        norm_x = (x - image_x) / image_width
        norm_y = 1- (y - image_y) / image_height

        window_width, window_height = Window.size
        scale_factor = min(window_width / image_width, window_height / image_height)

        norm_size = size*scale_factor 
        return norm_x, norm_y, norm_size

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
        text="""Please open this app in FULL-SCREEN and write your first name in the textbox and select your session type.
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
        self.session_type_dropdown = Spinner(size_hint_y=None, text='Select Session Type', height=40, values=['Origine', 'AI'], font_size='20sp')
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

    #ユーザーの一覧を記録したcsvの読み込み
    def read_user_csv(self, csv_file):
        user_data = []
        if os.path.exists(csv_file):
            with open(csv_file, 'r', newline='') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    user_data.append(row)
        return user_data
    
    #マーカーの太さを初期化する
    def initialize_line_width(self, dt):
        initial_line_slider_value = 5
        if self.draw_widget.parent:  # draw_widgetが親に追加されているか確認
            # ImageWidgetのnorm_image_sizeを使用してline_widthを計算
            self.draw_widget.line_width = int(initial_line_slider_value)
            self.on_line_width_change(None, initial_line_slider_value)  # line_width_sliderの値に基づいて再設定

    #セッションを開始する
    def start_session(self, instance):
        current_click_time = time.time()
        if current_click_time - self.last_click_time < 0.3: 
            global block
            block = 0
            user_id = self.selected_user_id

            self.layout.clear_widgets()
            # レイアウトの外縁に余白を追加
            self.layout.padding = [5, 5, 5, 5]
            self.layout.spacing = 18

            home_directory = os.path.expanduser('~')
            block += 1
            if self.session_type == 'Origine':
                block_folder_name = 'set_' + str(block)
                self.image_folder = os.path.join(home_directory, 'Interpretation_experiment', 'Origine', block_folder_name)
            elif self.session_type == 'AI':
                block_folder_name = 'set_' + str(block)
                self.image_folder = os.path.join(home_directory, 'Interpretation_experiment', 'AI', block_folder_name)

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
            self.clear_button = RadioButton(size_hint_y=None, height=15, text='erase all', group='mode', on_press=lambda instance: self.draw_widget.clear_canvas(), font_size='18sp', size_hint=(1, 1))

            mode_button_layout.add_widget(self.draw_mode_button)
            mode_button_layout.add_widget(self.erase_mode_button)
            mode_button_layout.add_widget(self.neutral_mode_button)
            mode_button_layout.add_widget(self.clear_button)

            initial_line_slider_value = 5 

            self.next_button = Button(size_hint_y=None, height=20,text='Next Image', on_press=self.next_image, size_hint=(1, 0.08), font_size='20sp')
            self.line_width_slider = Slider(min=1, max=10, value=initial_line_slider_value, size_hint=(1, 0.04))
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
            Clock.schedule_once(self.initialize_line_width, 0)
        self.last_click_time = current_click_time

    #confidenceのスライダー
    def on_slider_value_change(self, instance, value):
        self.confidence_label.text = f'Confidence: {int(value)}'

    #マーカーの太さを設定するスライダー
    def on_line_width_value_change(self, instance, value):
        self.line_width_label.text = f'Marker size: {int(value)}'

    #描図された領域内のデータ点を記録
    def generate_unique_points_set(self, normalized_points):
        unique_points = set()
        for x, y, size in normalized_points:
            radius = int(size / 2)
            center_x, center_y = int(pixel_size * x), int(pixel_size * y)

            # 探索範囲を決定し、点を追加（効率化）
            for dx in range(-radius, radius + 1):
                max_dy = int((radius**2 - dx**2)**0.5)  # dxに対する最大dyを計算
                for dy in range(-max_dy, max_dy + 1):
                    new_x = center_x + dx
                    new_y = center_y + dy
                    unique_points.add((new_x, new_y))

        return unique_points


    def store_efficiently(self, unique_points):
        # And this remains the same
        points_str = ';'.join([f'({x},{y})' for x, y in unique_points])
        return points_str
    
    def setup_session_layout(self):
        self.layout.clear_widgets()
        # レイアウトの外縁に余白を追加
        self.layout.padding = [5, 5, 5, 5]
        self.layout.spacing = 18

        image_widget_source = self.images[self.current_image_index]

        self.image_widget = Image(source=image_widget_source, allow_stretch=True, keep_ratio=True)
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
        self.clear_button = RadioButton(size_hint_y=None, height=15, text='erase all', group='mode', on_press=lambda instance: self.draw_widget.clear_canvas(), font_size='18sp', size_hint=(1, 1))

        mode_button_layout.add_widget(self.draw_mode_button)
        mode_button_layout.add_widget(self.erase_mode_button)
        mode_button_layout.add_widget(self.neutral_mode_button)
        mode_button_layout.add_widget(self.clear_button)

        initial_line_slider_value = 5 

        self.next_button = Button(size_hint_y=None, height=20,text='Next Image', on_press=self.next_image, size_hint=(1, 0.08), font_size='20sp')
        self.line_width_slider = Slider(min=1, max=10, value=initial_line_slider_value, size_hint=(1, 0.04))
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
        Clock.schedule_once(self.initialize_line_width, 0)
    
    #次のブロックのフォルダを選択
    def find_next_block_folder(self):
        folder_name = f"set_{block}"
        folder_path = os.path.join(os.path.expanduser('~'), 'Interpretation_experiment', f'{self.session_type}', folder_name)
        print(f"Searching for folder: {folder_path}")  # デバッグプリントを追加
        if os.path.exists(folder_path) and os.path.isdir(folder_path):
            return folder_path
        else:
            return None

    #アプリを終了する
    def stop_app(self):
        self.save_data_to_csv()
        self.stop()
    
    #休憩モードの実装
    def show_break_screen(self):
        self.layout.clear_widgets()  # 現在のウィジェットをクリア
        self.break_time_remaining = 10 * 60  # 休憩時間 (10分)
        
        # 休憩時間のラベル
        self.break_time_label = Label(text=f"Break Time: {self.break_time_remaining} seconds", font_size='20sp')
        self.layout.add_widget(self.break_time_label)
        
        # 休憩終了ボタン
        end_break_button = Button(text='End Break Early', on_press=self.check_double_click, size_hint=(1, 0.2), font_size='20sp')
        self.layout.add_widget(end_break_button)
        
        # タイマーを開始
        self.break_time_event = Clock.schedule_interval(self.update_break_time, 1)

    def check_double_click(self, instance):
        current_click_time = time.time()
        if current_click_time - self.last_click_time < 0.3:  # 0.3秒以内に再クリックされた場合はダブルクリックとみなす
            self.end_break(instance)
        self.last_click_time = current_click_time

    def update_break_time(self, dt):
        self.break_time_remaining -= 1
        self.break_time_label.text = f"Break Time: {self.break_time_remaining} seconds"
        
        if self.break_time_remaining <= 0:
            self.end_break(None)

    def end_break(self, instance):
        Clock.unschedule(self.break_time_event)  # タイマーを停止
        self.start_next_block()
    
    def start_next_block(self):
        next_folder = self.find_next_block_folder()
        print(next_folder)
        if next_folder:
            self.image_folder = next_folder
            self.images = [os.path.join(self.image_folder, f) for f in os.listdir(self.image_folder) if f.lower().endswith('.jpg')]
            self.current_image_index = 0
            if self.images:
                print('set_up')
                self.setup_session_layout()  # セッションのレイアウトを設定
            else:
                self.stop_app()
        else:
            self.stop_app()

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

            # True/Falseの値を取得
            abnormal_response = 'True' if self.true_radio_button.state == 'down' else 'False'

            # 画像パスを取得
            # save_folderの定義
            home_directory = os.path.expanduser('~')
            
            # 赤色の座標を取得して正規化
            raw_points = self.draw_widget.get_drawn_points()
            normalized_points = [(self.draw_widget.normalize_point(x, y, size)) for x, y, size in raw_points]
            # 512x512の画像サイズに対する相対座標に変換
            unique_points = self.generate_unique_points_set(normalized_points)
            points_str = self.store_efficiently(unique_points)
            
            # user_dataに必要なデータを追加する
            self.user_data.append([
                self.session_id, user_id, self.session_type, confidence, 
                round(elapsed_time, 2), conducted_time, image_name, 
                abnormal_response, points_str
            ])
            

            self.true_radio_button.state = 'normal'
            self.false_radio_button.state = 'normal'

            # 次の画像に進む前にマーカー情報をクリア
            self.draw_widget.clear_canvas()

            self.current_image_index += 1

            if self.current_image_index >= len(self.images):
                self.save_data_to_csv()  # 現在のセッションデータを保存
                global block
                block += 1 
                next_folder = self.find_next_block_folder()
                if next_folder:
                    self.show_break_screen()  # 休憩画面を表示
                else:
                    self.stop_app()  # 次のブロックがない場合はアプリを終了
            else:
                # 通常の画像表示ロジック
                self.image_widget.source = self.images[self.current_image_index]
                self.confidence_slider.value = 50
                self.confidence_label.text = 'Confidence: 50'
            
            # モードボタンの状態に基づいて描画モードを設定
            if self.draw_mode_button.state == 'down':
                self.draw_widget.set_draw_mode()
            elif self.erase_mode_button.state == 'down':
                self.draw_widget.set_erase_mode()
            elif self.neutral_mode_button.state == 'down':
                self.draw_widget.set_neutral_mode()

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
                writer.writerow(['session_id', 'user_id', 'session_type', 'confidence', 'reading_time', 'conducted_time', 'image_name', 'abnormal', 'drawn_points'])
            
            for data_row in self.user_data:
                writer.writerow(data_row)

        # CSVファイルへの書き込みが完了したらuser_dataをクリア
        self.user_data.clear()


    def on_line_width_change(self, instance, value):
        self.draw_widget.set_line_width(value)

if __name__ == '__main__':
    ImageViewerApp().run()
