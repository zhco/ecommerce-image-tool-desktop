# 电商图片处理工具 - 桌面版
import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.processor import ImageProcessor
from src.presets import PLATFORM_PRESETS


class EcommerceImageTool:
    def __init__(self, root):
        self.root = root
        self.root.title("电商图片处理工具 v1.0")
        self.root.geometry("900x680")
        self.root.minsize(800, 600)

        self.processor = ImageProcessor()
        self.current_image = None
        self.display_image = None
        self.processed_image = None
        self.files = []
        self.batch_mode = False

        self._setup_styles()
        self._build_ui()
        self._status("就绪 - 拖入图片或点击打开")

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#f0f0f0")
        style.configure("TLabelframe", background="#f0f0f0", borderwidth=1)
        style.configure("TLabelframe.Label", background="#f0f0f0", font=("", 10, "bold"))
        style.configure("TButton", padding=6, font=("", 10))
        style.configure("Accent.TButton", font=("", 11, "bold"))
        style.configure("TLabel", background="#f0f0f0", font=("", 10))
        style.configure("TEntry", font=("", 10))
        style.configure("Status.TLabel", background="#e0e0e0", relief="sunken", anchor="w", padding=(8, 4))

    def _build_ui(self):
        # === 主布局 ===
        main = ttk.Frame(self.root)
        main.pack(fill="both", expand=True)

        # 左侧面板
        left = ttk.Frame(main, width=320)
        left.pack(side="left", fill="y", padx=(10, 5), pady=10)
        left.pack_propagate(False)

        # 功能区
        ctrl = ttk.Labelframe(left, text="处理选项", padding=10)
        ctrl.pack(fill="x", pady=(0, 10))

        # 模式切换
        mode_frame = ttk.Frame(ctrl)
        mode_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(mode_frame, text="模式:").pack(side="left")
        self.mode_var = tk.StringVar(value="single")
        ttk.Radiobutton(mode_frame, text="单张", variable=self.mode_var, value="single", command=self._toggle_mode).pack(side="left", padx=5)
        ttk.Radiobutton(mode_frame, text="批量", variable=self.mode_var, value="batch", command=self._toggle_mode).pack(side="left", padx=5)

        # 选项
        self.bg_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(ctrl, text="AI 智能抠图 + 白底填充", variable=self.bg_var).pack(anchor="w", pady=2)

        self.enhance_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(ctrl, text="自动色彩增强", variable=self.enhance_var).pack(anchor="w", pady=2)

        # 尺寸预设
        size_frame = ttk.Frame(ctrl)
        size_frame.pack(fill="x", pady=(10, 5))
        ttk.Label(size_frame, text="平台尺寸:").pack(anchor="w")
        self.size_var = tk.StringVar(value="淘宝主图")
        self.size_combo = ttk.Combobox(size_frame, textvariable=self.size_var,
            values=list(PLATFORM_PRESETS.keys()), state="readonly", width=20)
        self.size_combo.pack(fill="x", pady=2)

        # 自定义尺寸
        custom_frame = ttk.Frame(ctrl)
        custom_frame.pack(fill="x", pady=2)
        ttk.Label(custom_frame, text="自定义:").pack(side="left")
        self.custom_w = ttk.Entry(custom_frame, width=5)
        self.custom_w.pack(side="left", padx=2)
        ttk.Label(custom_frame, text="×").pack(side="left")
        self.custom_h = ttk.Entry(custom_frame, width=5)
        self.custom_h.pack(side="left", padx=2)

        # 水印
        wm_frame = ttk.Frame(ctrl)
        wm_frame.pack(fill="x", pady=(10, 5))
        ttk.Label(wm_frame, text="水印文字:").pack(anchor="w")
        self.wm_var = tk.StringVar()
        ttk.Entry(wm_frame, textvariable=self.wm_var, width=25).pack(fill="x", pady=2)

        # 处理按钮
        btn_frame = ttk.Frame(ctrl)
        btn_frame.pack(fill="x", pady=(15, 0))
        self.process_btn = ttk.Button(btn_frame, text="▶ 开始处理", command=self._on_process, style="Accent.TButton")
        self.process_btn.pack(fill="x")

        # 进度条
        self.progress = ttk.Progressbar(ctrl, mode="indeterminate")

        # 文件列表（批量模式）
        self.file_frame = ttk.Labelframe(left, text="批量文件", padding=5)

        list_frame = ttk.Frame(self.file_frame)
        list_frame.pack(fill="both", expand=True)

        self.file_listbox = tk.Listbox(list_frame, height=6, font=("", 9))
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.file_listbox.yview)
        self.file_listbox.configure(yscrollcommand=scrollbar.set)
        self.file_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        btn_row = ttk.Frame(self.file_frame)
        btn_row.pack(fill="x", pady=(5, 0))
        ttk.Button(btn_row, text="+ 添加图片", command=self._add_files).pack(side="left")
        ttk.Button(btn_row, text="清空", command=self._clear_files).pack(side="left", padx=5)

        # 右侧预览区
        right = ttk.Frame(main)
        right.pack(side="right", fill="both", expand=True, padx=(5, 10), pady=10)

        preview_frame = ttk.Labelframe(right, text="预览", padding=5)
        preview_frame.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(preview_frame, bg="#e8e8e8", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        # 底部状态栏
        status_frame = ttk.Frame(self.root, height=28)
        status_frame.pack(side="bottom", fill="x")
        self.status_label = ttk.Label(status_frame, text="就绪", style="Status.TLabel")
        self.status_label.pack(fill="x")

        # 菜单栏
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="打开图片...", command=self._open_image, accelerator="Ctrl+O")
        file_menu.add_command(label="添加批量图片...", command=self._add_files, accelerator="Ctrl+D")
        file_menu.add_separator()
        file_menu.add_command(label="保存处理结果...", command=self._save_image, accelerator="Ctrl+S")
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)
        menubar.add_cascade(label="文件", menu=file_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="关于", command=self._about)
        menubar.add_cascade(label="帮助", menu=help_menu)
        self.root.config(menu=menubar)

        # 快捷键
        self.root.bind("<Control-o>", lambda e: self._open_image())
        self.root.bind("<Control-d>", lambda e: self._add_files())
        self.root.bind("<Control-s>", lambda e: self._save_image())

        self._toggle_mode()

    def _toggle_mode(self):
        self.batch_mode = self.mode_var.get() == "batch"
        if self.batch_mode:
            self.file_frame.pack(fill="x", pady=(0, 10))
        else:
            self.file_frame.pack_forget()
            self._clear_files()

    def _status(self, text):
        self.status_label.config(text=text)
        self.root.update_idletasks()

    def _add_files(self):
        files = filedialog.askopenfilenames(
            title="选择图片",
            filetypes=[("图片文件", "*.png *.jpg *.jpeg *.webp *.bmp *.tiff")]
        )
        for f in files:
            if f not in self.files:
                self.files.append(f)
                self.file_listbox.insert(tk.END, os.path.basename(f))
        self._status(f"已添加 {len(self.files)} 张图片")

    def _clear_files(self):
        self.files.clear()
        self.file_listbox.delete(0, tk.END)

    def _open_image(self):
        file = filedialog.askopenfilename(
            title="打开图片",
            filetypes=[("图片文件", "*.png *.jpg *.jpeg *.webp *.bmp *.tiff")]
        )
        if file:
            self.files = [file]
            self.current_image = Image.open(file)
            self._show_image(self.current_image)
            self._status(f"已打开: {os.path.basename(file)}")

    def _show_image(self, img):
        cw = self.canvas.winfo_width() or 500
        ch = self.canvas.winfo_height() or 450
        iw, ih = img.size
        ratio = min(cw / iw, ch / ih, 1.0)
        nw, nh = int(iw * ratio), int(ih * ratio)
        resized = img.resize((nw, nh), Image.LANCZOS)
        self.display_image = ImageTk.PhotoImage(resized)

        self.canvas.delete("all")
        self.canvas.config(width=cw, height=ch)
        x, y = (cw - nw) // 2, (ch - nh) // 2
        self.canvas.create_image(x, y, anchor="nw", image=self.display_image)

    def _save_image(self):
        if self.processed_image is None:
            messagebox.showwarning("提示", "没有处理结果可保存")
            return
        file = filedialog.asksaveasfilename(
            title="保存图片",
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg"), ("WebP", "*.webp")]
        )
        if file:
            self.processed_image.save(file)
            self._status(f"已保存: {os.path.basename(file)}")
            messagebox.showinfo("完成", f"图片已保存至:\n{file}")

    def _get_options(self):
        size_name = self.size_var.get()
        if size_name == "自定义尺寸":
            try:
                w, h = int(self.custom_w.get()), int(self.custom_h.get())
                target_size = (w, h)
            except ValueError:
                target_size = None
        else:
            target_size = PLATFORM_PRESETS.get(size_name)

        return {
            "remove_bg": self.bg_var.get(),
            "fill_bg": self.bg_var.get(),
            "bg_color": (255, 255, 255),
            "auto_enhance": self.enhance_var.get(),
            "target_size": target_size,
            "watermark_text": self.wm_var.get().strip() or None,
            "watermark_position": "br",
            "watermark_opacity": 100,
        }

    def _on_process(self):
        if self.batch_mode:
            self._run_batch()
        else:
            self._run_single()

    def _run_single(self):
        if not self.files:
            messagebox.showwarning("提示", "请先打开一张图片")
            return
        self._start_progress()
        threading.Thread(target=self._process_single, daemon=True).start()

    def _process_single(self):
        try:
            img = Image.open(self.files[0])
            options = self._get_options()
            result = self.processor.process(img, options)
            self.processed_image = result["image"].convert("RGB")
            self.root.after(0, lambda: self._on_single_done(result["steps"]))
        except Exception as e:
            self.root.after(0, lambda: self._on_error(str(e)))

    def _on_single_done(self, steps):
        self._stop_progress()
        self._show_image(self.processed_image)
        msg = " → ".join(steps)
        self._status(f"处理完成: {msg}")
        messagebox.showinfo("完成", f"处理完成!\n{msg}\n\n请使用 Ctrl+S 或 文件→保存 导出")

    def _run_batch(self):
        if not self.files:
            messagebox.showwarning("提示", "请先添加图片")
            return
        output_dir = filedialog.askdirectory(title="选择输出目录")
        if not output_dir:
            return

        self._start_progress()
        threading.Thread(target=self._process_batch, args=(output_dir,), daemon=True).start()

    def _process_batch(self, output_dir):
        options = self._get_options()
        total = len(self.files)
        success = 0
        errors = []

        for i, f in enumerate(self.files):
            try:
                self.root.after(0, lambda msg=f"处理中 {i+1}/{total}: {os.path.basename(f)}": self._status(msg))
                img = Image.open(f)
                result = self.processor.process(img, options)
                name, ext = os.path.splitext(os.path.basename(f))
                out_path = os.path.join(output_dir, f"{name}_processed.png")
                result["image"].convert("RGB").save(out_path)
                success += 1
            except Exception as e:
                errors.append(f"{os.path.basename(f)}: {e}")

        self.root.after(0, lambda: self._on_batch_done(success, total, errors, output_dir))

    def _on_batch_done(self, success, total, errors, output_dir):
        self._stop_progress()
        msg = f"完成 {success}/{total} 张"
        if errors:
            msg += f"\n失败 {len(errors)} 张:\n" + "\n".join(errors[:5])
        self._status(msg)
        messagebox.showinfo("批量完成", f"已处理 {success}/{total} 张图片\n输出目录: {output_dir}")

    def _on_error(self, msg):
        self._stop_progress()
        self._status(f"错误: {msg}")
        messagebox.showerror("处理失败", str(msg))

    def _start_progress(self):
        self.process_btn.config(state="disabled")
        self.progress.pack(fill="x", pady=(5, 0))
        self.progress.start()

    def _stop_progress(self):
        self.process_btn.config(state="normal")
        self.progress.stop()
        self.progress.pack_forget()

    def _about(self):
        messagebox.showinfo("关于", "电商图片处理工具 v1.0\n\n"
            "功能: AI 抠图 / 白底填充 / 20+ 平台尺寸 / 批量处理\n"
            "技术: rembg (U2-Net) + Pillow\n"
            "仓库: github.com/zhco/ecommerce-image-tool-desktop")


if __name__ == "__main__":
    root = tk.Tk()
    app = EcommerceImageTool(root)
    root.mainloop()
