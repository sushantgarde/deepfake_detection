# app.py
import os
import json
import time
import asyncio
import logging
import requests
import threading
import customtkinter as ctk
from tkinter import filedialog, messagebox
from realitydefender import RealityDefender
from json import JSONDecodeError
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# ======= CONFIG: put your Reality Defender API key here (or set RD_API_KEY env var) =======
API_KEY = "rd_d31c254c9efee9e4_f2f69faa775771b7ed29650eb2edc58a"  # <-- paste your key here (keep quotes) or export env RD_API_KEY
# ========================================================================================

# Polling / retry parameters
UPLOAD_RETRIES = 4
UPLOAD_BACKOFF = 2  # seconds base backoff
MEDIA_POLL_TIMEOUT = 300  # seconds (5 minutes)
MEDIA_POLL_INTERVAL = 3  # seconds between polls
MEDIA_DETAIL_URL = "https://api.prd.realitydefender.xyz/api/media/users/{request_id}"

# Configure logging
log_filename = f"deepfake_detector_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class DeepfakeDetectorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Deepfake Detection System (Reality Defender)")
        self.root.geometry("900x650")

        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.API_KEY = API_KEY or os.environ.get("RD_API_KEY")
        if not self.API_KEY:
            logger.error("API Key missing")
            messagebox.showerror("API Key missing",
                                 "Put your Reality Defender API key in API_KEY variable or set RD_API_KEY env var.")
            self.root.destroy()
            return

        # init SDK client (still used for upload convenience)
        try:
            self.rd_client = RealityDefender(api_key=self.API_KEY)
            logger.info("Reality Defender client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Reality Defender client: {e}", exc_info=True)
            messagebox.showerror("Initialization Error", f"Failed to initialize Reality Defender client: {e}")
            self.root.destroy()
            return

        self.selected_file = None
        self.is_analyzing = False
        self.analysis_thread = None

        # Create a persistent event loop in a background thread
        self.loop = None
        self.loop_thread = None
        self._start_background_loop()

        self.setup_ui()

        logger.info("Application started successfully")

    def _start_background_loop(self):
        """Start a persistent event loop in a background thread"""

        def run_loop():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            logger.info("Background event loop started")
            self.loop.run_forever()

        self.loop_thread = threading.Thread(target=run_loop, daemon=True)
        self.loop_thread.start()

        # Wait for loop to be ready
        while self.loop is None:
            time.sleep(0.01)

    def setup_ui(self):
        title_label = ctk.CTkLabel(
            self.root,
            text="Deepfake Detection System (Reality Defender)",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.pack(pady=12)

        subtitle = ctk.CTkLabel(
            self.root,
            text="Upload an image or audio file. (Video: paid plans)",
            font=ctk.CTkFont(size=12)
        )
        subtitle.pack(pady=2)

        main = ctk.CTkFrame(self.root)
        main.pack(padx=16, pady=16, fill="both", expand=True)

        file_frame = ctk.CTkFrame(main)
        file_frame.pack(fill="x", pady=8)

        self.file_label = ctk.CTkLabel(file_frame, text="No file selected", anchor="w")
        self.file_label.pack(side="left", padx=10, pady=8, fill="x", expand=True)

        select_btn = ctk.CTkButton(file_frame, text="Select File", width=120, command=self.upload_file)
        select_btn.pack(side="right", padx=8)

        action_frame = ctk.CTkFrame(main)
        action_frame.pack(fill="x", pady=6)

        self.analyze_btn = ctk.CTkButton(
            action_frame,
            text="Analyze",
            command=self.analyze_file,
            width=140
        )
        self.analyze_btn.pack(side="left", padx=6)

        clear_btn = ctk.CTkButton(
            action_frame,
            text="Clear",
            command=self.clear_results,
            width=120,
            fg_color="#dc3545"
        )
        clear_btn.pack(side="left", padx=6)

        export_btn = ctk.CTkButton(
            action_frame,
            text="Export Result",
            command=self.export_results,
            width=120
        )
        export_btn.pack(side="right", padx=6)

        # Progress bar
        self.progress = ctk.CTkProgressBar(main)
        self.progress.pack(fill="x", pady=8, padx=12)
        self.progress.set(0)
        self.progress.pack_forget()  # Hidden by default

        self.results_frame = ctk.CTkFrame(main)
        self.results_frame.pack(fill="both", expand=True, pady=8)

        results_title = ctk.CTkLabel(
            self.results_frame,
            text="Detection Result",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        results_title.pack(pady=6)

        self.result_label = ctk.CTkLabel(
            self.results_frame,
            text="Ready. Select a file and click Analyze.",
            font=ctk.CTkFont(size=14)
        )
        self.result_label.pack(padx=12, pady=20)

        self.raw_text = ctk.CTkTextbox(self.results_frame, width=780, height=220)
        self.raw_text.pack(padx=12, pady=8, fill="both", expand=True)
        self.raw_text.insert("1.0", "Raw API output will appear here after analysis.\n")
        self.raw_text.configure(state="disabled")
        self.raw_text.pack_forget()  # hidden by default

        self.status_label = ctk.CTkLabel(self.root, text="Ready", anchor="w")
        self.status_label.pack(side="bottom", fill="x", padx=6, pady=6)

    def upload_file(self):
        """File selection dialog"""
        try:
            logger.info("Opening file selection dialog")
            file_path = filedialog.askopenfilename(
                title="Select Image or Audio File",
                filetypes=[
                    ("Image/Audio", "*.jpg *.jpeg *.png *.bmp *.webp *.mp3 *.wav *.m4a *.aac *.ogg *.flac"),
                    ("All files", "*.*")
                ]
            )
            if file_path:
                self.selected_file = file_path
                filename = os.path.basename(file_path)
                self.file_label.configure(text=filename)
                self.update_status(f"Selected: {filename}")
                logger.info(f"File selected: {file_path}")
        except Exception as e:
            logger.error(f"Error in file selection: {e}", exc_info=True)
            messagebox.showerror("File Selection Error", f"Error selecting file: {e}")

    def clear_results(self):
        """Clear all results and reset UI"""
        try:
            logger.info("Clearing results")
            self.selected_file = None
            self.file_label.configure(text="No file selected")
            self.result_label.configure(text="Ready. Select a file and click Analyze.")
            self.raw_text.configure(state="normal")
            self.raw_text.delete("1.0", "end")
            self.raw_text.insert("1.0", "Raw API output will appear here after analysis.\n")
            self.raw_text.configure(state="disabled")
            self.raw_text.pack_forget()
            self.progress.pack_forget()
            self.update_status("Ready")
            logger.info("Results cleared successfully")
        except Exception as e:
            logger.error(f"Error clearing results: {e}", exc_info=True)

    def export_results(self):
        """Export analysis results to file"""
        try:
            logger.info("Exporting results")
            text = self.result_label.cget("text")

            if text == "Ready. Select a file and click Analyze.":
                messagebox.showinfo("No Results", "No results to export. Please analyze a file first.")
                return

            out_path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text file", "*.txt"), ("All files", "*.*")]
            )
            if out_path:
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(f"Deepfake Detection Results\n")
                    f.write(f"{'=' * 50}\n\n")
                    f.write(f"Result: {text}\n\n")
                    f.write(f"{'=' * 50}\n")
                    f.write("Raw API response:\n\n")
                    f.write(self.raw_text.get("1.0", "end"))
                logger.info(f"Results exported to: {out_path}")
                messagebox.showinfo("Exported", f"Results exported to:\n{out_path}")
        except Exception as e:
            logger.error(f"Error exporting results: {e}", exc_info=True)
            messagebox.showerror("Export Error", f"Failed to export results: {e}")

    def update_status(self, message):
        """Thread-safe status update"""
        try:
            self.root.after(0, lambda: self.status_label.configure(text=message))
            logger.info(f"Status: {message}")
        except Exception as e:
            logger.error(f"Error updating status: {e}")

    def update_progress(self, value):
        """Thread-safe progress update"""
        try:
            self.root.after(0, lambda: self.progress.set(value))
        except Exception as e:
            logger.error(f"Error updating progress: {e}")

    def analyze_file(self):
        """Start analysis in separate thread to prevent UI freezing"""
        if self.is_analyzing:
            logger.warning("Analysis already in progress")
            messagebox.showinfo("Please Wait", "Analysis already in progress. Please wait.")
            return

        if not self.selected_file:
            logger.warning("No file selected for analysis")
            messagebox.showwarning("No File", "Please select a file first.")
            return

        if not os.path.exists(self.selected_file):
            logger.error(f"Selected file does not exist: {self.selected_file}")
            messagebox.showerror("File Error", "Selected file no longer exists.")
            return

        try:
            size_mb = os.path.getsize(self.selected_file) / (1024 * 1024)
            logger.info(f"File size: {size_mb:.2f} MB")
            if size_mb > 250:
                if not messagebox.askyesno("Large File", f"The file is {size_mb:.1f} MB. Continue?"):
                    logger.info("User cancelled large file upload")
                    return
        except Exception as e:
            logger.error(f"Error checking file size: {e}", exc_info=True)

        # Start analysis in separate thread
        self.is_analyzing = True
        self.analyze_btn.configure(state="disabled", text="Analyzing...")
        self.progress.pack(fill="x", pady=8, padx=12)
        self.update_progress(0)

        logger.info(f"Starting analysis thread for file: {self.selected_file}")
        self.analysis_thread = threading.Thread(target=self._run_analysis, daemon=True)
        self.analysis_thread.start()

    def _run_analysis(self):
        """Run analysis in background thread using persistent event loop"""
        try:
            logger.info("Analysis thread started")
            self.update_status("Uploading file...")
            self.update_progress(0.1)

            try:
                # Upload file using the persistent event loop
                future = asyncio.run_coroutine_threadsafe(
                    self.safe_upload(self.selected_file, retries=UPLOAD_RETRIES, backoff=UPLOAD_BACKOFF),
                    self.loop
                )
                upload_resp = future.result(timeout=120)  # 2 minute timeout for upload

                if isinstance(upload_resp, dict) and upload_resp.get("error"):
                    logger.error(f"Upload failed: {upload_resp}")
                    self._show_error_result("Upload failed. See raw response below.", upload_resp)
                    return

                # Extract request_id from upload response
                request_id = None
                try:
                    request_id = upload_resp.get("request_id") or upload_resp.get("id") or upload_resp.get("job_id")
                    logger.info(f"Request ID: {request_id}")
                except Exception as e:
                    logger.error(f"Error extracting request_id: {e}", exc_info=True)
                    self._show_error_result(
                        "Upload failed (unexpected response).",
                        {"upload_resp": str(upload_resp), "error": str(e)}
                    )
                    return

                if not request_id:
                    logger.error("No request_id in upload response")
                    self._show_error_result("Upload failed (no request_id).", upload_resp)
                    return

                self.update_status(f"Request ID: {request_id} - Analyzing...")
                self.update_progress(0.3)
                logger.info(f"Starting to poll for results (request_id: {request_id})")

                # Poll the media detail endpoint
                start = time.time()
                final = None
                poll_count = 0

                while time.time() - start < MEDIA_POLL_TIMEOUT:
                    poll_count += 1
                    elapsed = time.time() - start
                    progress = 0.3 + (elapsed / MEDIA_POLL_TIMEOUT) * 0.6
                    self.update_progress(min(progress, 0.9))

                    logger.info(f"Poll attempt {poll_count} (elapsed: {elapsed:.1f}s)")
                    md = self.get_media_detail(request_id)

                    # If an 'error' key exists -> show it and break
                    if isinstance(md, dict) and md.get("error"):
                        logger.error(f"Media detail error: {md}")
                        self._show_error_result("Analysis failed (media detail error).", md)
                        return

                    # Check resultsSummary
                    rs = md.get("resultsSummary") or {}
                    status = (rs.get("status") or "").upper()
                    metadata = rs.get("metadata") or {}
                    finalScore = metadata.get("finalScore")

                    logger.info(f"Poll {poll_count}: status={status}, finalScore={finalScore}")

                    # Check for final status
                    if status in ("AUTHENTIC", "FAKE", "SUSPICIOUS", "NOT_APPLICABLE", "UNABLE_TO_EVALUATE"):
                        logger.info(f"Final status received: {status}")
                        final = {"status": status, "finalScore": finalScore, "raw": md}
                        break

                    time.sleep(MEDIA_POLL_INTERVAL)

                if final is None:
                    logger.warning("Analysis timed out")
                    self._show_error_result(
                        "Analysis timed out. Please try again.",
                        md or {"note": "no response", "timeout": MEDIA_POLL_TIMEOUT}
                    )
                    return

                # Process final result
                self.update_progress(1.0)
                self._show_success_result(final)

            except TimeoutError:
                logger.error("Upload operation timed out")
                self._show_error_result(
                    "Upload timed out. Please check your connection and try again.",
                    {"error": "upload_timeout"}
                )
            except Exception as e:
                logger.error(f"Error during analysis: {e}", exc_info=True)
                self._show_error_result(
                    f"Analysis error: {str(e)}",
                    {"exception": str(e), "type": type(e).__name__}
                )

        except Exception as e:
            logger.error(f"Unhandled exception in analysis: {e}", exc_info=True)
            self._show_error_result(
                f"Analysis failed with exception: {str(e)}",
                {"exception": str(e), "type": type(e).__name__}
            )
        finally:
            self.is_analyzing = False
            self.root.after(0, lambda: self.analyze_btn.configure(state="normal", text="Analyze"))
            logger.info("Analysis thread finished")

    async def safe_upload(self, file_path, retries=UPLOAD_RETRIES, backoff=UPLOAD_BACKOFF):
        """Upload with retries (handles transient server errors)"""
        attempt = 0
        last_exc = None

        while attempt < retries:
            try:
                logger.info(f"Upload attempt {attempt + 1}/{retries}")
                resp = await self.rd_client.upload(file_path=file_path)
                logger.info("Upload successful")
                return resp
            except Exception as e:
                last_exc = e
                logger.warning(f"Upload attempt {attempt + 1} failed: {e}")
                if attempt < retries - 1:
                    wait_time = backoff * (attempt + 1)
                    logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                attempt += 1

        logger.error(f"All upload attempts failed: {last_exc}")
        return {"error": f"upload_failed: {str(last_exc)}"}

    def get_media_detail(self, request_id, retries=5, backoff=2):
        """Call the Media Detail endpoint directly (synchronous)"""
        url = MEDIA_DETAIL_URL.format(request_id=request_id)
        headers = {"X-API-KEY": self.API_KEY}
        attempt = 0
        last_text = None

        while attempt < retries:
            try:
                logger.info(f"Media detail request attempt {attempt + 1}/{retries}")
                r = requests.get(url, headers=headers, timeout=15)

                # if success (2xx) try JSON
                if 200 <= r.status_code < 300:
                    try:
                        result = r.json()
                        logger.info(f"Media detail response received (status {r.status_code})")
                        return result
                    except (ValueError, JSONDecodeError) as e:
                        logger.error(f"Invalid JSON response: {e}")
                        return {"error": f"invalid_json_response (status {r.status_code})", "body": r.text[:500]}
                else:
                    # server error (502, 5xx) -> retry after backoff
                    last_text = f"HTTP {r.status_code}: {r.text[:1000]}"
                    logger.warning(f"HTTP error {r.status_code}, response: {r.text[:200]}")

                    # for 4xx we probably shouldn't retry (auth / bad request)
                    if 400 <= r.status_code < 500:
                        logger.error(f"Client error (4xx): {r.status_code}")
                        return {"error": f"HTTP_{r.status_code}", "body": r.text[:500]}

            except requests.exceptions.Timeout as e:
                last_text = f"Request timeout: {str(e)}"
                logger.warning(f"Request timeout on attempt {attempt + 1}")
            except requests.exceptions.RequestException as e:
                last_text = f"Request exception: {str(e)}"
                logger.warning(f"Request exception on attempt {attempt + 1}: {e}")
            except Exception as e:
                last_text = str(e)
                logger.error(f"Unexpected error in media detail request: {e}", exc_info=True)

            attempt += 1
            if attempt < retries:
                wait_time = backoff * attempt
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)

        logger.error(f"All media detail attempts failed: {last_text}")
        return {"error": "media_detail_failed", "detail": last_text}

    def _show_success_result(self, final):
        """Display successful analysis result"""
        try:
            status = final.get("status")
            score = final.get("finalScore")

            logger.info(f"Displaying success result: status={status}, score={score}")

            # Map to UI label
            label_text = "Analysis completed but unclear result."
            color = "#ffffff"

            if status == "AUTHENTIC":
                label_text = "✓ NOT AI GENERATED"
                color = "#28a745"
            elif status == "FAKE":
                label_text = "✗ AI GENERATED"
                color = "#dc3545"
            elif status == "SUSPICIOUS":
                label_text = "⚠ AI GENERATED (Suspicious)"
                color = "#ffc107"
            elif status == "NOT_APPLICABLE":
                label_text = "○ NOT APPLICABLE (No evaluation criteria met)"
                color = "#6c757d"
            elif status == "UNABLE_TO_EVALUATE":
                label_text = "? UNABLE TO EVALUATE (error during analysis)"
                color = "#fd7e14"

            # Fallback to finalScore threshold (0-100)
            if (not status or status == "") and (score is not None):
                try:
                    sc = float(score)
                    logger.info(f"Using finalScore for determination: {sc}")
                    if sc >= 50:
                        label_text = "✗ AI GENERATED"
                        color = "#dc3545"
                    else:
                        label_text = "✓ NOT AI GENERATED"
                        color = "#28a745"
                except Exception as e:
                    logger.error(f"Error parsing finalScore: {e}")

            if score is not None:
                label_text += f" (Score: {score})"

            # Update UI
            self.root.after(0, lambda: self.result_label.configure(text=label_text, text_color=color))
            self._show_raw_response(final.get("raw", {}), title="Media Detail (Final Result)")
            self.update_status("Analysis complete ✓")
            logger.info("Success result displayed")

        except Exception as e:
            logger.error(f"Error displaying success result: {e}", exc_info=True)

    def _show_error_result(self, message, raw_data):
        """Display error result"""
        try:
            logger.info(f"Displaying error result: {message}")
            self.root.after(0, lambda: self.result_label.configure(text=message, text_color="#dc3545"))
            self._show_raw_response(raw_data, title="Error Details")
            self.update_status("Analysis failed ✗")
        except Exception as e:
            logger.error(f"Error displaying error result: {e}", exc_info=True)

    def _show_raw_response(self, raw, title="API Response"):
        """Display raw API response"""
        try:
            body = json.dumps(raw, indent=2)
        except Exception as e:
            logger.warning(f"Could not serialize raw response to JSON: {e}")
            body = str(raw)

        def update_ui():
            try:
                self.raw_text.configure(state="normal")
                self.raw_text.delete("1.0", "end")
                self.raw_text.insert("1.0", f"{title}\n{'=' * 50}\n\n{body}")
                self.raw_text.configure(state="disabled")
                self.raw_text.pack(fill="both", expand=True)
            except Exception as e:
                logger.error(f"Error updating raw text display: {e}", exc_info=True)

        self.root.after(0, update_ui)

    def on_closing(self):
        """Handle window close event"""
        if self.is_analyzing:
            if messagebox.askokcancel("Analysis in Progress", "Analysis is still running. Do you want to quit?"):
                logger.info("User closed application during analysis")
                # Stop the event loop
                if self.loop and self.loop.is_running():
                    self.loop.call_soon_threadsafe(self.loop.stop)
                self.root.destroy()
        else:
            logger.info("Application closed")
            # Stop the event loop
            if self.loop and self.loop.is_running():
                self.loop.call_soon_threadsafe(self.loop.stop)
            self.root.destroy()


def main():
    logger.info("=" * 60)
    logger.info("Deepfake Detection System Starting")
    logger.info(f"Log file: {log_filename}")
    logger.info("=" * 60)

    try:
        root = ctk.CTk()
        app = DeepfakeDetectorApp(root)
        root.mainloop()
    except Exception as e:
        logger.critical(f"Critical error in main: {e}", exc_info=True)
        messagebox.showerror("Critical Error", f"Application failed to start: {e}")
    finally:
        logger.info("Application shutdown")


if __name__ == "__main__":
    main()