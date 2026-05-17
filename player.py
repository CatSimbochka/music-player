import os
import sys
import tkinter as tk
from tkinter import filedialog
import customtkinter as ctk
from PIL import Image, ImageTk
import pygame
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC
import io
import random

# Initialize pygame mixer
pygame.mixer.init()

class MusicPlayer(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Плеер от симбы")
        self.geometry("900x600")
        
        # Initial settings
        if getattr(sys, 'frozen', False):
            # If the application is run as a bundle, the PyInstaller bootloader
            # extends the sys module by a flag frozen=True and sets the app 
            # path into variable _MEIPASS'.
            application_path = os.path.dirname(sys.executable)
        else:
            application_path = os.path.dirname(os.path.abspath(__file__))

        self.music_dir = os.path.join(application_path, "music")
        if not os.path.exists(self.music_dir):
            os.makedirs(self.music_dir)
            
        self.playlist = []
        self.original_playlist = []
        self.current_song_index = -1
        self.playing = False
        self.current_song_length = 0
        self.shuffle_mode = False
        self.repeat_mode = False # 0: no repeat, 1: repeat all, 2: repeat one
        self.gradient_colors = ["#ff5f6d", "#ffc371"] # Default red-pinkish gradient
        
        # UI Setup
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Sidebar for settings
        self.sidebar = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_remove() # Hidden by default
        
        self.setup_sidebar()
        
        # Main content area
        self.main_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew")
        
        # Background Canvas for gradient
        self.bg_canvas = tk.Canvas(self.main_frame, highlightthickness=0)
        self.bg_canvas.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.bg_canvas.bind("<Configure>", lambda e: self.draw_gradient())
        
        self.setup_main_ui()
        
        # Load music
        self.load_music()
        
        # Update progress bar
        self.update_progress()

    def setup_sidebar(self):
        label = ctk.CTkLabel(self.sidebar, text="Настройки", font=ctk.CTkFont(size=20, weight="bold"))
        label.pack(pady=20, padx=10)
        
        # Predefined gradients
        ctk.CTkLabel(self.sidebar, text="Предустановки:").pack(pady=5)
        presets = {
            "Закат (Красно-розовый)": ["#ff5f6d", "#ffc371"],
            "Океан (Синий)": ["#2193b0", "#6dd5ed"],
            "Лес (Зеленый)": ["#11998e", "#38ef7d"],
            "Полночь (Темный)": ["#232526", "#414345"]
        }
        
        for name, colors in presets.items():
            btn = ctk.CTkButton(self.sidebar, text=name, command=lambda c=colors: self.set_gradient(c))
            btn.pack(pady=5, padx=10)
            
        # Custom color picker (simplified for now)
        ctk.CTkLabel(self.sidebar, text="Свой градиент:").pack(pady=(20, 5))
        
        self.color1_btn = ctk.CTkButton(self.sidebar, text="Цвет 1", command=lambda: self.pick_color(0))
        self.color1_btn.pack(pady=5, padx=10)
        
        self.color2_btn = ctk.CTkButton(self.sidebar, text="Цвет 2", command=lambda: self.pick_color(1))
        self.color2_btn.pack(pady=5, padx=10)

    def setup_main_ui(self):
        # Settings toggle button
        self.settings_btn = ctk.CTkButton(self.main_frame, text="⚙", width=40, command=self.toggle_sidebar)
        self.settings_btn.place(relx=0.95, rely=0.05, anchor="ne")
        
        # Album Art
        self.album_art_label = ctk.CTkLabel(self.main_frame, text="", width=250, height=250, fg_color="gray")
        self.album_art_label.pack(pady=(50, 10))
        
        # Song Info
        self.song_label = ctk.CTkLabel(self.main_frame, text="Выберите песню", font=ctk.CTkFont(size=18, weight="bold"))
        self.song_label.pack()
        
        self.artist_label = ctk.CTkLabel(self.main_frame, text="Исполнитель", font=ctk.CTkFont(size=14))
        self.artist_label.pack()
        
        # Controls
        controls_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        controls_frame.pack(pady=20)
        
        self.prev_btn = ctk.CTkButton(controls_frame, text="⏮", width=50, command=self.prev_song)
        self.prev_btn.grid(row=0, column=0, padx=10)
        
        self.play_btn = ctk.CTkButton(controls_frame, text="▶", width=60, command=self.toggle_play)
        self.play_btn.grid(row=0, column=1, padx=10)
        
        self.next_btn = ctk.CTkButton(controls_frame, text="⏭", width=50, command=self.next_song)
        self.next_btn.grid(row=0, column=2, padx=10)

        self.shuffle_btn = ctk.CTkButton(controls_frame, text="🔀", width=40, command=self.toggle_shuffle, fg_color="gray")
        self.shuffle_btn.grid(row=0, column=3, padx=5)

        self.repeat_btn = ctk.CTkButton(controls_frame, text="🔁", width=40, command=self.toggle_repeat, fg_color="gray")
        self.repeat_btn.grid(row=0, column=4, padx=5)
        
        # Progress Bar
        self.progress_bar = ctk.CTkProgressBar(self.main_frame, width=400)
        self.progress_bar.pack(pady=10)
        self.progress_bar.set(0)
        
        # Volume
        volume_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        volume_frame.pack(pady=10)
        ctk.CTkLabel(volume_frame, text="🔈").grid(row=0, column=0, padx=5)
        self.volume_slider = ctk.CTkSlider(volume_frame, from_=0, to=1, command=self.set_volume)
        self.volume_slider.grid(row=0, column=1, padx=5)
        self.volume_slider.set(0.7)
        pygame.mixer.music.set_volume(0.7)
        
        # Playlist
        self.playlist_box = tk.Listbox(self.main_frame, bg="#2b2b2b", fg="white", selectbackground="#ff5f6d", bd=0, highlightthickness=0)
        self.playlist_box.pack(fill="both", expand=True, padx=50, pady=20)
        self.playlist_box.bind("<Double-Button-1>", self.play_selected)

    def draw_gradient(self):
        self.bg_canvas.delete("gradient")
        width = self.bg_canvas.winfo_width()
        height = self.bg_canvas.winfo_height()
        
        (r1, g1, b1) = self.hex_to_rgb(self.gradient_colors[0])
        (r2, g2, b2) = self.hex_to_rgb(self.gradient_colors[1])
        
        for i in range(height):
            r = int(r1 + (r2 - r1) * (i / height))
            g = int(g1 + (g2 - g1) * (i / height))
            b = int(b1 + (b2 - b1) * (i / height))
            color = f"#{r:02x}{g:02x}{b:02x}"
            self.bg_canvas.create_line(0, i, width, i, fill=color, tags="gradient")
        
        self.bg_canvas.tag_lower("gradient")

    def hex_to_rgb(self, hex_color):
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def set_gradient(self, colors):
        self.gradient_colors = colors
        self.draw_gradient()

    def pick_color(self, index):
        from tkinter import colorchooser
        color = colorchooser.askcolor(title=f"Выберите цвет {index+1}")[1]
        if color:
            self.gradient_colors[index] = color
            self.draw_gradient()

    def toggle_sidebar(self):
        if self.sidebar.winfo_viewable():
            self.sidebar.grid_remove()
        else:
            self.sidebar.grid()

    def load_music(self):
        self.playlist = sorted([f for f in os.listdir(self.music_dir) if f.endswith(".mp3")])
        self.original_playlist = self.playlist.copy()
        self.update_playlist_box()

    def update_playlist_box(self):
        self.playlist_box.delete(0, tk.END)
        for song in self.playlist:
            self.playlist_box.insert(tk.END, song)

    def play_song(self, index):
        if 0 <= index < len(self.playlist):
            self.current_song_index = index
            song_path = os.path.join(self.music_dir, self.playlist[index])
            pygame.mixer.music.load(song_path)
            pygame.mixer.music.play()
            self.playing = True
            self.play_btn.configure(text="⏸")
            self.update_song_info(song_path)
            
            # Cache song length for progress bar
            try:
                audio = MP3(song_path)
                self.current_song_length = audio.info.length
            except:
                self.current_song_length = 0

            # Select in listbox
            self.playlist_box.selection_clear(0, tk.END)
            self.playlist_box.selection_set(index)
            self.playlist_box.see(index)

    def toggle_play(self):
        if not self.playlist:
            return
        
        if self.current_song_index == -1:
            self.play_song(0)
        elif self.playing:
            pygame.mixer.music.pause()
            self.playing = False
            self.play_btn.configure(text="▶")
        else:
            pygame.mixer.music.unpause()
            self.playing = True
            self.play_btn.configure(text="⏸")

    def play_selected(self, event):
        selection = self.playlist_box.curselection()
        if selection:
            self.play_song(selection[0])

    def next_song(self):
        if not self.playlist: return
        next_idx = (self.current_song_index + 1) % len(self.playlist)
        if next_idx == 0 and self.repeat_mode == 0:
            return # Stop at the end if no repeat
        self.play_song(next_idx)

    def prev_song(self):
        if not self.playlist: return
        prev_idx = (self.current_song_index - 1) % len(self.playlist)
        self.play_song(prev_idx)

    def toggle_shuffle(self):
        self.shuffle_mode = not self.shuffle_mode
        if self.shuffle_mode:
            self.shuffle_btn.configure(fg_color=["#3B8ED0", "#1F538D"]) # ctk default blue
            current_song = self.playlist[self.current_song_index] if self.current_song_index != -1 else None
            random.shuffle(self.playlist)
            if current_song:
                self.current_song_index = self.playlist.index(current_song)
        else:
            self.shuffle_btn.configure(fg_color="gray")
            current_song = self.playlist[self.current_song_index] if self.current_song_index != -1 else None
            self.playlist = self.original_playlist.copy()
            if current_song:
                self.current_song_index = self.playlist.index(current_song)
        self.update_playlist_box()

    def toggle_repeat(self):
        self.repeat_mode = (self.repeat_mode + 1) % 3
        if self.repeat_mode == 0:
            self.repeat_btn.configure(text="🔁", fg_color="gray")
        elif self.repeat_mode == 1:
            self.repeat_btn.configure(text="🔁", fg_color=["#3B8ED0", "#1F538D"])
        else:
            self.repeat_btn.configure(text="🔂", fg_color=["#3B8ED0", "#1F538D"])

    def set_volume(self, val):
        pygame.mixer.music.set_volume(float(val))

    def update_song_info(self, song_path):
        # Update labels
        try:
            audio = MP3(song_path, ID3=ID3)
            title = audio.get('TIT2', os.path.basename(song_path))
            artist = audio.get('TPE1', 'Неизвестный исполнитель')
            self.song_label.configure(text=str(title))
            self.artist_label.configure(text=str(artist))
            
            # Load album art
            image_data = None
            for tag in audio.tags.values():
                if isinstance(tag, APIC):
                    image_data = tag.data
                    break
            
            if image_data:
                img = Image.open(io.BytesIO(image_data))
                img = img.resize((250, 250), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.album_art_label.configure(image=photo, text="")
                self.album_art_label.image = photo
            else:
                self.album_art_label.configure(image="", text="Нет обложки")
                
        except Exception as e:
            self.song_label.configure(text=os.path.basename(song_path))
            self.artist_label.configure(text="Неизвестный исполнитель")
            self.album_art_label.configure(image="", text="Нет обложки")

    def update_progress(self):
        if self.playing:
            try:
                # This is a bit tricky with pygame as it doesn't give current pos easily for seeking
                # but we can at least show it's playing
                curr = pygame.mixer.music.get_pos() / 1000 # milliseconds to seconds
                if self.current_song_index != -1 and self.current_song_length > 0:
                    self.progress_bar.set(curr / self.current_song_length)
                    
                    if not pygame.mixer.music.get_busy() and self.playing:
                        if self.repeat_mode == 2:
                            self.play_song(self.current_song_index)
                        else:
                            self.next_song()
            except:
                pass
        
        self.after(1000, self.update_progress)

if __name__ == "__main__":
    app = MusicPlayer()
    app.mainloop()
