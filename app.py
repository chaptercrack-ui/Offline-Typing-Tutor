import tkinter as tk
from tkinter import ttk, filedialog
import random
import time
from typing import List

# ---------------------------
# Default word list
# ---------------------------
DEFAULT_WORDS = (
    "the be to of and a in that have I it for not on with he as you do at "
    "this but his by from they we say her she or an will my one all would "
    "there their what so up out if about who get which go me when make can "
    "like time no just him know take people into year your good some could "
    "them see other than then now look only come its over think also back "
    "after use two how our work first well way even new want because any "
    "these give day most us"
).split()

def load_word_file(path: str) -> List[str]:
    words = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                for w in line.strip().split():
                    if w:
                        words.append(w.strip())
    except Exception as e:
        raise
    return words

# ---------------------------
# TypingTutorApp Class
# ---------------------------
class TypingTutorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Offline Typing Tutor By Shawon")
        self.geometry("900x600")
        self.minsize(800, 500)

        # App state
        self.word_list = DEFAULT_WORDS[:]
        self.display_words = []
        self.word_index = 0
        self.typed_words = []
        self.current_typed = ""
        self.test_running = False
        self.time_limit_seconds = 60
        self.start_time = None
        self.timer_job = None
        self.display_stream_size = 200

        # Build UI
        self._build_controls()
        self._build_display_area()
        self._build_entry_area()
        self._reset_state_clear_display()

    # -----------------------
    # UI building helpers
    # -----------------------
    def _build_controls(self):
        control_frame = ttk.Frame(self)
        control_frame.pack(fill="x", padx=10, pady=8)

        presets_frame = ttk.Frame(control_frame)
        presets_frame.pack(side="left", padx=(0, 12))
        ttk.Label(presets_frame, text="Time:").pack(side="left", padx=(0, 6))
        for t in (30, 60, 120, 300):
            b = ttk.Button(presets_frame, text=f"{t}s", command=lambda secs=t: self.set_time_limit(secs))
            b.pack(side="left", padx=4)

        manual_frame = ttk.Frame(control_frame)
        manual_frame.pack(side="left", padx=(0,12))
        ttk.Label(manual_frame, text="Custom (seconds):").pack(side="left")
        self.manual_time_var = tk.StringVar(value=str(self.time_limit_seconds))
        self.manual_time_entry = ttk.Entry(manual_frame, width=6, textvariable=self.manual_time_var)
        self.manual_time_entry.pack(side="left", padx=(6,0))
        ttk.Button(manual_frame, text="Set", command=self._set_time_from_entry).pack(side="left", padx=6)

        ttk.Button(control_frame, text="Load word file...", command=self._on_load_word_file).pack(side="left", padx=6)
        self.start_button = ttk.Button(control_frame, text="Start Test", command=self.start_test)
        self.start_button.pack(side="left", padx=6)
        self.reset_button = ttk.Button(control_frame, text="Reset", command=self.reset_test)
        self.reset_button.pack(side="left", padx=6)
        self.timer_label = ttk.Label(control_frame, text="Time left: 00:00")
        self.timer_label.pack(side="right", padx=(0, 10))

    def _build_display_area(self):
        display_frame = ttk.Frame(self)
        display_frame.pack(fill="both", expand=True, padx=10, pady=(0,8))

        self.text_widget = tk.Text(display_frame, wrap="word", font=("Consolas", 14), padx=8, pady=8)
        self.text_widget.pack(side="left", fill="both", expand=True)
        self.text_widget.config(state="disabled")

        vsb = ttk.Scrollbar(display_frame, orient="vertical", command=self.text_widget.yview)
        vsb.pack(side="right", fill="y")
        self.text_widget['yscrollcommand'] = vsb.set

        self.text_widget.tag_configure("correct", foreground="green")
        self.text_widget.tag_configure("incorrect", foreground="red")
        self.text_widget.tag_configure("current", background="#e6f0ff")
        self.text_widget.tag_configure("partial-incorrect", foreground="#b22222")

    def _build_entry_area(self):
        entry_frame = ttk.Frame(self)
        entry_frame.pack(fill="x", padx=10, pady=(0,10))

        ttk.Label(entry_frame, text="Type here:").pack(side="left", padx=(0,8))
        self.entry_var = tk.StringVar()
        self.entry = ttk.Entry(entry_frame, textvariable=self.entry_var, font=("Consolas", 16))
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<KeyRelease>", self._on_key_release)
        self.entry.bind("<space>", self._on_space_pressed)
        self.entry.focus_set()

        self.live_stats_label = ttk.Label(entry_frame, text="WPM: 0 | Correct: 0 | Incorrect: 0 | Accuracy: 0%")
        self.live_stats_label.pack(side="right", padx=(10,0))

    # -----------------------
    # State / Display utilities
    # -----------------------
    def _reset_state_clear_display(self):
        self.display_words = []
        self.word_index = 0
        self.typed_words = []
        self.current_typed = ""
        self.test_running = False
        self.start_time = None
        if self.timer_job:
            self.after_cancel(self.timer_job)
            self.timer_job = None
        self._update_timer_label(self.time_limit_seconds)
        self._refresh_text_widget_initial()

    def _refresh_text_widget_initial(self):
        self._ensure_display_words(self.display_stream_size)
        self._render_text_stream()
        self.entry_var.set("")
        self.entry.config(state="normal")
        self.live_stats_label.config(text="WPM: 0 | Correct: 0 | Incorrect: 0 | Accuracy: 0%")

    def _ensure_display_words(self, n):
        while len(self.display_words) - self.word_index < n:
            self.display_words.extend(self._generate_words_batch(100))

    def _generate_words_batch(self, n):
        if not self.word_list:
            return [""] * n
        return [random.choice(self.word_list) for _ in range(n)]

    def _render_text_stream(self):
        start = max(0, self.word_index)
        end = min(len(self.display_words), start + self.display_stream_size)
        words_to_show = self.display_words[start:end]
        full_text = " ".join(words_to_show)

        self.text_widget.config(state="normal")
        self.text_widget.delete("1.0", "end")
        self.text_widget.insert("1.0", full_text)

        for tag in ("correct", "incorrect", "current", "partial-incorrect"):
            self.text_widget.tag_remove(tag, "1.0", "end")

        cursor_pos = 0
        for i, w in enumerate(words_to_show):
            word_start = f"1.0 + {cursor_pos} chars"
            word_end = f"1.0 + {cursor_pos + len(w)} chars"
            typed_i = i
            if typed_i < len(self.typed_words):
                expected, typed, correct = self.typed_words[typed_i]
                tag = "correct" if correct else "incorrect"
                self.text_widget.tag_add(tag, word_start, word_end)
            cursor_pos += len(w) + 1

        # Current word highlighting
        if len(words_to_show) > 0:
            cp = 0
            cur_word = words_to_show[0]
            cs = f"1.0 + {cp} chars"
            ce = f"1.0 + {cp + len(cur_word)} chars"
            self.text_widget.tag_add("current", cs, ce)

            typed_partial = self.current_typed
            if typed_partial:
                prefix = cur_word[:len(typed_partial)]
                typed_start = cp
                typed_end = cp + len(typed_partial)
                tstart = f"1.0 + {typed_start} chars"
                tend = f"1.0 + {typed_end} chars"
                self.text_widget.tag_remove("partial-incorrect", tstart, tend)
                if typed_partial != prefix:
                    self.text_widget.tag_add("partial-incorrect", tstart, tend)

        self.text_widget.config(state="disabled")

    # -----------------------
    # Event handlers
    # -----------------------
    def _on_load_word_file(self):
        path = filedialog.askopenfilename(title="Open word file", filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if not path:
            return
        try:
            words = load_word_file(path)
            if not words:
                tk.messagebox.showwarning("Load words", "Selected file did not contain any words.")
                return
            self.word_list = words
            tk.messagebox.showinfo("Load words", f"Loaded {len(words)} words from file.")
            self._reset_state_clear_display()
        except Exception as e:
            tk.messagebox.showerror("Load words", f"Error loading file: {e}")

    def _set_time_from_entry(self):
        try:
            s = int(self.manual_time_var.get())
            if s <= 0:
                raise ValueError("Time must be > 0")
            self.set_time_limit(s)
        except Exception:
            tk.messagebox.showerror("Invalid time", "Please enter a valid integer number of seconds.")

    def set_time_limit(self, seconds: int):
        if self.test_running:
            tk.messagebox.showwarning("Test running", "Cannot change time while a test is running. Reset first.")
            return
        self.time_limit_seconds = seconds
        self.manual_time_var.set(str(seconds))
        self._update_timer_label(seconds)

    def start_test(self):
        if self.test_running:
            return
        self.display_words = []
        self.typed_words = []
        self.word_index = 0
        self.current_typed = ""
        self._ensure_display_words(self.display_stream_size)
        self._render_text_stream()
        self.entry_var.set("")
        self.entry.focus_set()
        self.test_running = True
        self.start_time = time.time()
        self._update_timer_label(self.time_limit_seconds)
        self._timer_tick()

    def reset_test(self):
        if self.test_running:
            self.test_running = False
            if self.timer_job:
                self.after_cancel(self.timer_job)
                self.timer_job = None
        self._reset_state_clear_display()
        self.entry.bind("<space>", self._on_space_pressed)

    def _timer_tick(self):
        if not self.test_running:
            return
        now = time.time()
        elapsed = now - self.start_time
        remaining = self.time_limit_seconds - elapsed
        if remaining <= 0:
            self.test_running = False
            self._update_timer_label(0)
            self.entry.config(state="disabled")
            self.entry.unbind("<space>")
            self._finalize_results()
            return
        else:
            self._update_timer_label(int(remaining))
            self.timer_job = self.after(100, self._timer_tick)

    def _update_timer_label(self, seconds_left):
        m, s = divmod(seconds_left, 60)
        self.timer_label.config(text=f"Time left: {int(m):02d}:{int(s):02d}")

    def _on_key_release(self, event):
        if not self.test_running:
            return
        self.current_typed = self.entry_var.get()

    def _on_space_pressed(self, event):
        if not self.test_running:
            return "break"
        typed = self.entry_var.get().strip()
        if typed:
            expected = self.display_words[self.word_index]
            correct = typed == expected
            self.typed_words.append((expected, typed, correct))
            self.word_index += 1
            self.current_typed = ""
            self.entry_var.set("")
            self._ensure_display_words(self.display_stream_size)
            self._render_text_stream()
            self._update_live_stats()
        return "break"

    def _update_live_stats(self):
        correct_count = sum(1 for w in self.typed_words if w[2])
        incorrect_count = len(self.typed_words) - correct_count
        elapsed = max(1, time.time() - self.start_time) if self.start_time else 1
        wpm = correct_count / elapsed * 60  # Corrected: use actual typing time
        accuracy = (correct_count / max(1, len(self.typed_words))) * 100 if self.typed_words else 0
        self.live_stats_label.config(text=f"WPM: {int(wpm)} | Correct: {correct_count} | Incorrect: {incorrect_count} | Accuracy: {accuracy:.1f}%")

    # -----------------------
    # Final results (centered modal)
    # -----------------------
    def _finalize_results(self):
        correct_count = sum(1 for w in self.typed_words if w[2])
        incorrect_count = len(self.typed_words) - correct_count
        elapsed = max(1, time.time() - self.start_time)  # Use actual typing time
        wpm = correct_count / elapsed * 60
        accuracy = (correct_count / max(1, len(self.typed_words))) * 100 if self.typed_words else 0

        summary_text = (
            f"WPM: {int(wpm)}\n"
            f"Correct Words: {correct_count}\n"
            f"Incorrect Words: {incorrect_count}\n"
            f"Accuracy: {accuracy:.1f} %"
        )

        # Create a custom Toplevel window
        result_win = tk.Toplevel(self)
        result_win.title("Typing Test Results")
        result_win.resizable(False, False)

        # Center the popup
        window_width = 350
        window_height = 180
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = int((screen_width / 2) - (window_width / 2))
        y = int((screen_height / 2) - (window_height / 2))
        result_win.geometry(f"{window_width}x{window_height}+{x}+{y}")

        # Display results
        label = tk.Label(result_win, text=summary_text, font=("Consolas", 14), justify="left")
        label.pack(padx=20, pady=20, anchor="w")

        # Make modal (user must close X to continue)
        result_win.transient(self)
        result_win.grab_set()
        result_win.focus_set()


# ---------------------------
# Run App
# ---------------------------
if __name__ == "__main__":
    app = TypingTutorApp()
    app.mainloop()


# echo "# Offline-Typing-Tutor" >> README.md
# git init
# git add README.md
# git commit -m "first commit"
# git branch -M main
# git remote add origin https://github.com/chaptercrack-ui/Offline-Typing-Tutor.git
# git push -u origin main