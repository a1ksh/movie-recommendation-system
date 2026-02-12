import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import webbrowser
from PIL import Image, ImageTk
import pygame
import requests
from io import BytesIO
import json
import os
import hashlib

POSTER_FOLDER = "img_cache"
os.makedirs(POSTER_FOLDER, exist_ok=True)
poster_cache = {}
POSTER_FOLDER = "img_cache"
os.makedirs(POSTER_FOLDER, exist_ok=True)

df = pd.read_csv("filmmbd1.csv", encoding="utf-8", sep=';')
df.columns = df.columns.str.strip()


df['rating'] = pd.to_numeric(df['rating'], errors='coerce')
df = df.dropna(subset=['rating'])
df['rating'] = df['rating'].astype(float)

genre_cols = [c for c in df.columns if c.startswith('genre/')]
df['genre'] = df[genre_cols].values.tolist()
df['genre'] = df['genre'].apply(lambda lst: [str(g) for g in lst if pd.notna(g)])

sim_cols = [c for c in df.columns if c.startswith('similar/')]
df['similar'] = df[sim_cols].values.tolist()
df['similar'] = df['similar'].apply(lambda lst: [str(s) for s in lst if pd.notna(s)])

if 'trivia' not in df.columns: df['trivia'] = ''
if 'trailer_url' not in df.columns: df['trailer_url'] = None
if 'poster_url' not in df.columns: df['poster_url'] = None
watch_cols = [c for c in df.columns if c.startswith('watch_')]
frame_a2 = None

movies = df.to_dict(orient='records')
all_titles = [m['title'] for m in movies]
all_genres = sorted({g for m in movies for g in m['genre']})

mood_map = {
    "Қуанышты": ["Комедия", "Анимация", "Семейный", "Мультфильм"],
    "Қайғылы": ["Драма", "Романтика", "Мелодрама"],
    "Напряжение": ["Криминал", "Детектив", "Триллер"],
    "Фантазия": ["Фэнтези", "Приключения", "Фантастика"],
}

def resize_image(path, width=1000):
    img = Image.open(path)
    w_percent = (width / float(img.size[0]))
    h_size = int((float(img.size[1]) * float(w_percent)))
    img = img.resize((width, h_size), Image.LANCZOS)
    return ImageTk.PhotoImage(img)


def load_poster(url):
    if not url or pd.isna(url):
        return ImageTk.PhotoImage(Image.new('RGB', (100, 150), color='#333'))

    if url in poster_cache:
        return poster_cache[url]

    file_hash = hashlib.md5(url.encode()).hexdigest()
    local_path = os.path.join(POSTER_FOLDER, f"{file_hash}.jpg")


    if os.path.exists(local_path):
        try:
            img = Image.open(local_path).resize((100, 150))
            poster = ImageTk.PhotoImage(img)
            poster_cache[url] = poster
            return poster
        except:
            pass


    try:
        if url.startswith('http'):
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            img = Image.open(BytesIO(response.content)).resize((100, 150))
        else:
            img = Image.open(url).resize((100, 150))

        img.save(local_path)

        poster = ImageTk.PhotoImage(img)
        poster_cache[url] = poster
        return poster
    except Exception as e:
        print(f"Ошибка загрузки постера: {e}")
        return ImageTk.PhotoImage(Image.new('RGB', (100, 150), color='#333'))


def save_watchlist():
    with open(watchlist_file, "w", encoding="utf-8") as f:
        json.dump(watchlist, f, indent=2, ensure_ascii=False)
def add_to_watchlist(title, list_type):
    if title not in watchlist[list_type]:
        watchlist[list_type].append(title)
        save_watchlist()

watchlist_file = "watchlist.json"
watchlist = {"watched": [], "wishlist": []}
if os.path.exists(watchlist_file):
    try:
        with open(watchlist_file, "r", encoding="utf-8") as f:
            data = f.read().strip()
            if data:
                watchlist = json.loads(data)
            else:
                save_watchlist()
    except json.JSONDecodeError:
        print("Файл watchlist.json повреждён. Пересоздаём.")
        save_watchlist()

def remove_from_watchlist(title, list_type):
    if title in watchlist[list_type]:
        watchlist[list_type].remove(title)
        save_watchlist()
        open_watchlist(lambda: show_frame(frame_a2))


def display_movies(movie_list, root_frame, enumerate_items=False):
    for widget in root_frame.winfo_children():
        widget.destroy()

    canvas = tk.Canvas(root_frame)
    scrollbar = ttk.Scrollbar(root_frame, orient="vertical", command=canvas.yview)
    scroll_frame = ttk.Frame(canvas)

    scroll_frame.bind(
        "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    canvas.create_window((0, 0), window=scroll_frame, anchor='nw')
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    for idx, m in enumerate(movie_list, 1 if enumerate_items else 0):
        bg = '#d4edda' if m['rating'] >= 9 else '#fff3cd' if m['rating'] >= 8 else '#f8f9fa'
        frm = tk.Frame(scroll_frame, bg=bg, bd=1, relief='solid', pady=5, padx=5)
        frm.pack(fill='x', padx=5, pady=5)

        img_frame = tk.Frame(frm, bg=bg)
        img_frame.pack(side='left', padx=5)
        img = load_poster(m.get('poster_url'))
        if img:
            tk.Label(img_frame, image=img, bg=bg).pack()
            frm.image = img

        info_frame = tk.Frame(frm, bg=bg)
        info_frame.pack(side='left', fill='x', expand=True)

        title_text = f"{idx}. {m['title']} ({m['year']})" if enumerate_items else f"{m['title']} ({m['year']})"
        tk.Label(info_frame, text=title_text, font=('Segoe UI', 12, 'bold'), bg=bg).pack(fill='x')
        tk.Label(info_frame, text=f"{m['duration']} мин | {'/'.join(m['genre'])}", bg=bg).pack(fill='x')
        tk.Label(info_frame, text=f"Рейтинг: {m['rating']}/10", bg=bg).pack(fill='x')

        btn_frame = tk.Frame(frm, bg=bg)
        btn_frame.pack(side='right', padx=5)

        if m.get('trailer_url'):
            ttk.Button(btn_frame, text='▶ Трейлер', command=lambda u=m['trailer_url']: webbrowser.open(u)).pack(pady=2)

        for col in watch_cols:
            url = m.get(col)
            if pd.notna(url):
                svc = col.split('_', 1)[1].title()
                ttk.Button(btn_frame, text=svc, command=lambda u=url: webbrowser.open(u)).pack(pady=2)

        title = m['title']

        if title in watchlist['watched']:
            ttk.Button(btn_frame, text="Жою", command=lambda t=title: remove_from_watchlist(t, "watched")).pack(pady=2)
        else:
            ttk.Button(btn_frame, text="✅ Көрдім", command=lambda t=title: add_to_watchlist(t, "watched")).pack(pady=2)

        if title in watchlist['wishlist']:
            ttk.Button(btn_frame, text="Жою", command=lambda t=title: remove_from_watchlist(t, "wishlist")).pack(pady=2)
        else:
            ttk.Button(btn_frame, text="📌 Көргім келеді", command=lambda t=title: add_to_watchlist(t, "wishlist")).pack(pady=2)

def open_watchlist(back_callback):
    frame = tk.Frame(root)
    ttk.Label(frame, text="Менің тізімім", font=('Segoe UI', 16, 'bold')).pack(pady=10)

    tabs = ttk.Notebook(frame)
    tab1 = ttk.Frame(tabs)
    tab2 = ttk.Frame(tabs)
    tabs.add(tab1, text="✅ Көрдім")
    tabs.add(tab2, text="📌 Көргім келеді")
    tabs.pack(fill='both', expand=True)

    seen = [m for m in movies if m['title'] in watchlist['watched']]
    want = [m for m in movies if m['title'] in watchlist['wishlist']]

    display_movies(seen, tab1)
    display_movies(want, tab2)
    ttk.Button(frame, text="Артқа", command=back_callback).pack(pady=10)
    show_frame(frame)

def open_genre(back_callback):
    frame = tk.Frame(root)

    gvar = tk.StringVar()
    dvar = tk.IntVar(value=120)

    top_frame = ttk.Frame(frame)
    top_frame.pack(fill='x', padx=10, pady=5)
    ttk.Label(top_frame, text="Жанрды таңдаңыз:").pack(side='left', padx=5)
    genre_combo = ttk.Combobox(top_frame, textvariable=gvar, values=all_genres, width=25)
    genre_combo.pack(side='left', padx=5)
    ttk.Label(top_frame, text="Максималды ұзақтығы (мин):").pack(side='left', padx=5)
    duration_slider = tk.Scale(top_frame, from_=60, to=300, orient=tk.HORIZONTAL, variable=dvar, length=150)
    duration_slider.pack(side='left', padx=5)

    display_area = ttk.Frame(frame)
    display_area.pack(fill='both', expand=True)

    def find_by_genre():
        genre = gvar.get()
        if not genre:
            messagebox.showwarning("Ескерту", "Жанрды таңдаңыз!")
            return
        sel = [m for m in movies if genre in m['genre'] and m['duration'] <= dvar.get()]
        sel.sort(key=lambda x: x['rating'], reverse=True)
        display_movies(sel, display_area)

    ttk.Button(top_frame, text="Табу", command=find_by_genre).pack(side='left', padx=10)
    ttk.Button(frame, text="Артқа", command=back_callback).pack(pady=10)

    show_frame(frame)

def open_similar(back_callback):
    frame = tk.Frame(root)
    svar = tk.StringVar()

    top_frame = ttk.Frame(frame)
    top_frame.pack(fill='x', padx=10, pady=5)
    ttk.Label(top_frame, text="Фильм атауы:").pack(side='left', padx=5)
    title_combo = ttk.Combobox(top_frame, textvariable=svar, values=all_titles, width=40)
    title_combo.pack(side='left', padx=5)

    display_area = ttk.Frame(frame)
    display_area.pack(fill='both', expand=True)

    def find_similar():
        title = svar.get().strip().lower()
        base = next((m for m in movies if m['title'].lower() == title), None)
        if not base:
            messagebox.showinfo("Ақпарат", "Фильм табылмады")
            return
        similar_titles = base.get('similar', [])
        sel = [m for m in movies if m['title'] in similar_titles and m['title'] != base['title']]
        display_movies(sel, display_area)

    ttk.Button(top_frame, text="Ұқсас фильмдер", command=find_similar).pack(side='left', padx=5)
    ttk.Button(frame, text="Артқа", command=back_callback).pack(pady=10)

    show_frame(frame)

def open_mood(back_callback):
    frame = tk.Frame(root)
    mvar = tk.StringVar()

    top_frame = ttk.Frame(frame)
    top_frame.pack(fill='x', padx=10, pady=10)
    ttk.Label(top_frame, text="Көңіл-күйді таңдаңыз:").pack(side='left', padx=5)
    mood_combo = ttk.Combobox(top_frame, textvariable=mvar, values=list(mood_map.keys()), width=20)
    mood_combo.pack(side='left', padx=5)

    display_area = ttk.Frame(frame)
    display_area.pack(fill='both', expand=True)

    def find_by_mood():
        mood = mvar.get()
        target_genres = mood_map.get(mood, [])
        sel = [m for m in movies if any(g in m['genre'] for g in target_genres)]
        sel.sort(key=lambda x: x['rating'], reverse=True)
        display_movies(sel, display_area)

    ttk.Button(top_frame, text="Ұсыныс", command=find_by_mood).pack(side='left', padx=10)
    ttk.Button(frame, text="Артқа", command=back_callback).pack(pady=10)

    show_frame(frame)

def open_top_movies(back_callback):
    frame = tk.Frame(root)
    ttk.Label(frame, text="ТОП-10 Фильмдер", font=('Segoe UI', 16, 'bold')).pack(pady=10)

    display_area = ttk.Frame(frame)
    display_area.pack(fill='both', expand=True)

    top10 = sorted(movies, key=lambda m: m['rating'], reverse=True)[:10]
    display_movies(top10, display_area, enumerate_items=True)
    ttk.Button(frame, text="Артқа", command=back_callback).pack(pady=10)

    show_frame(frame)

def show_frame(frame):
    for widget in root.winfo_children():
        widget.pack_forget()
    frame.pack(fill='both', expand=True)


def show_meme_frame():
    meme_frame = tk.Frame(root)
    meme_frame.pack(fill="both", expand=True)

    img = Image.open("mask.jpg")
    img = img.resize((1000, 700), Image.LANCZOS)
    tk_img = ImageTk.PhotoImage(img)

    canvas = tk.Canvas(meme_frame, width=1000, height=700)
    canvas.pack()

    canvas.create_image(0, 0, anchor="nw", image=tk_img)
    canvas.image = tk_img
    ok_button = ttk.Button(canvas, text="ОК", command=root.quit)
    canvas.create_window(500, 670, window=ok_button)
    show_frame(meme_frame)

def main():
    global root
    pygame.mixer.init()
    pygame.mixer.music.load("hans-zimmer-time.mp3")
    pygame.mixer.music.play()

    global root
    global frame_a2

    global root
    root = tk.Tk()
    root.title("Фильм ұсыныс жүйесі")
    root.geometry("1000x700")

    frame_a1 = tk.Frame(root)
    bg = resize_image("a1.jpg")
    canvas1 = tk.Canvas(frame_a1, width=bg.width(), height=bg.height())
    canvas1.pack()
    canvas1.create_image(0, 0, anchor="nw", image=bg)
    canvas1.image = bg

    frame_a2 = tk.Frame(root)
    bg2 = resize_image("a2.jpg")
    canvas2 = tk.Canvas(frame_a2, width=bg2.width(), height=bg2.height())
    canvas2.pack()
    canvas2.create_image(0, 0, anchor="nw", image=bg2)
    canvas2.image = bg2

    def go_to_a2():
        show_frame(frame_a2)

    tk.Button(frame_a1, text="ИӘ", command=go_to_a2, width=16, height=2, bg="#B79BC8").place(x=393, y=240)
    tk.Button(frame_a1, text="ЖОҚ", command=show_meme_frame, width=16, height=2, bg="#B79BC8").place(x=521, y=240)

    def make_open(func):
        return lambda: func(lambda: show_frame(frame_a2))

    tk.Button(frame_a2, text="OK", command=make_open(open_genre), width=17, height=2, bg="#A2E4E5").place(x=322, y=126)
    tk.Button(frame_a2, text="OK", command=make_open(open_similar), width=17, height=2, bg="#A59FE5").place(x=538, y=240)
    tk.Button(frame_a2, text="OK", command=make_open(open_mood), width=17, height=2, bg="#CBA0E7").place(x=327, y=445)
    tk.Button(frame_a2, text="OK", command=make_open(open_top_movies), width=17, height=2, bg="#E5A0CD").place(x=537, y=625)
    tk.Button(frame_a2, text="OK", command=make_open(open_watchlist), width=17, height=2, bg="#A0E5B9").place(x=90, y=310)

    show_frame(frame_a1)
    root.mainloop()

if __name__ == '__main__':
    main()