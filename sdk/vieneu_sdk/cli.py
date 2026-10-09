"""
cli.py — Giao diện dòng lệnh CLI cho VieNeu Client SDK.
"""

import argparse
import sys
from pathlib import Path

from vieneu_sdk.client import VieneuClient
from vieneu_sdk.processor import NovelBatchProcessor


def main():
    parser = argparse.ArgumentParser(
        description="VieNeu Novel-to-Video CLI — Chuyển đổi folder truyện thành MP4 YouTube & Lifecycle Control",
    )

    parser.add_argument(
        "--folder", "-i",
        type=Path,
        default=None,
        help="Thư mục chứa các file text chapter (.txt)",
    )
    parser.add_argument(
        "--cover", "-c",
        type=Path,
        default=None,
        help="Đường dẫn file ảnh bìa tĩnh (JPG/PNG)",
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=None,
        help="Thư mục xuất file video MP4 kết quả",
    )
    parser.add_argument(
        "--server", "-s",
        default="http://100.90.61.115:7865",
        help="Địa chỉ VieNeu GPU Server (Mặc định: http://100.90.61.115:7865)",
    )
    parser.add_argument(
        "--voice", "-v",
        default="Ngọc Huyền",
        help="Giọng đọc tiểu thuyết (Mặc định: Ngọc Huyền)",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=1.2,
        help="Tốc độ đọc (Mặc định: 1.2)",
    )
    parser.add_argument(
        "--start",
        type=int,
        default=None,
        help="Số thứ tự chương bắt đầu (Ví dụ: 1)",
    )
    parser.add_argument(
        "--end",
        type=int,
        default=None,
        help="Số thứ tự chương kết thúc (Ví dụ: 50)",
    )
    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=None,
        help="Số lượng chương tối đa cần render",
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Không dùng checkpoint, ép buộc render lại toàn bộ",
    )

    # --- LỰA CHỌN LIFECYCLE CONTROLLER ---
    parser.add_argument(
        "--gpu-status",
        action="store_true",
        help="Truy vấn trạng thái GPU, VRAM và Idle Watchdog từ xa",
    )
    parser.add_argument(
        "--load-gpu",
        action="store_true",
        help="Yêu cầu Server nạp model VieNeu lên VRAM GPU ngay lập tức",
    )
    parser.add_argument(
        "--unload-gpu",
        action="store_true",
        help="Yêu cầu Server rút model khỏi VRAM GPU, giải phóng bộ nhớ về 0 MB",
    )

    # --- CÁC TÙY CHỌN YOUTUBE UPLOAD ---
    parser.add_argument(
        "--upload-youtube",
        action="store_true",
        help="Tự động upload video MP4 lên YouTube API v3 sau khi render xong",
    )
    parser.add_argument(
        "--novel-title",
        default="Tiểu Thuyết",
        help="Tên bộ truyện dùng để đặt tiêu đề YouTube chuẩn SEO",
    )
    parser.add_argument(
        "--privacy",
        default="unlisted",
        choices=["private", "unlisted", "public"],
        help="Quyền riêng tư YouTube: private | unlisted | public (Mặc định: unlisted)",
    )
    parser.add_argument(
        "--playlist",
        default=None,
        help="ID Playlist YouTube tự động thêm video vào",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=None,
        help="Đường dẫn file .env chứa YOUTUBE_CLIENT_ID và YOUTUBE_CLIENT_SECRET",
    )

    args = parser.parse_args()
    client = VieneuClient(base_url=args.server)

    # Lệnh điều khiển GPU thuần túy
    if args.gpu_status:
        try:
            st = client.get_gpu_status()
            print("📊 GPU SERVER LIFECYCLE STATUS:")
            print(f"  • Trạng thái (FSM): {st.get('state')}")
            print(f"  • VRAM Allocated:  {st.get('vram_allocated_mb', 0):.1f} MB")
            print(f"  • Worker PID:      {st.get('worker_pid')}")
            print(f"  • Watchdog Idle:   {st.get('idle_seconds_remaining', 0):.1f}s remaining")
        except Exception as e:
            print(f"❌ Lỗi truy vấn trạng thái GPU: {e}")
        return

    if args.load_gpu:
        try:
            res = client.load_gpu(voice_preload=[args.voice])
            print("⚡ ĐÃ NẠP MODEL LÊN GPU VRAM:")
            print(f"  • Result: {res}")
        except Exception as e:
            print(f"❌ Lỗi khi yêu cầu nạp GPU: {e}")
        return

    if args.unload_gpu:
        try:
            res = client.unload_gpu()
            print("❄️ ĐÃ THU HỒI VRAM GPU VỀ 0 MB:")
            print(f"  • Result: {res}")
        except Exception as e:
            print(f"❌ Lỗi khi yêu cầu xả GPU: {e}")
        return

    if not args.folder or not args.cover or not args.output:
        parser.error("Cần truyền đủ --folder, --cover, --output khi thực hiện render batch!")

    print(f"🚀 Khởi chạy VieNeu Novel-to-Video Pipeline...")
    print(f"  • GPU Server: {args.server}")
    print(f"  • Thư mục input: {args.folder}")
    print(f"  • Ảnh bìa: {args.cover}")
    print(f"  • Output: {args.output}")
    print(f"  • Giọng đọc: {args.voice} (Tốc độ {args.speed}x)")
    if getattr(args, "upload_youtube", False):
        print(f"  • Tự động đăng YouTube: BẬT (Quyền: {args.privacy})")
    print()

    try:
        health = client.check_health()
        print(f"✅ Kết nối GPU Server thành công! Status: {health.get('status')}")
    except Exception as e:
        print(f"⚠️ Không thể kết nối tới GPU Server: {e}")

    youtube_uploader = None
    if args.upload_youtube:
        try:
            from vieneu_sdk.youtube.config import YouTubeConfig
            from vieneu_sdk.youtube.auth import YouTubeAuthManager
            from vieneu_sdk.youtube.uploader import YouTubeUploader

            yt_config = YouTubeConfig.from_env(env_path=args.env_file)
            yt_auth = YouTubeAuthManager(yt_config)
            youtube_uploader = YouTubeUploader(auth_manager=yt_auth)
            print("✅ Đã khởi tạo YouTube Uploader sẵn sàng!")
        except Exception as e:
            print(f"⚠️ Lỗi khởi tạo YouTube Uploader: {e}. Tiến hành render offline...")

    processor = NovelBatchProcessor(client=client)
    summary = processor.process(
        folder_path=args.folder,
        cover_path=args.cover,
        output_dir=args.output,
        voice=args.voice,
        speed=args.speed,
        start_chapter=args.start,
        end_chapter=args.end,
        limit=args.limit,
        resume=not args.no_resume,
        auto_upload_youtube=args.upload_youtube,
        youtube_privacy=args.privacy,
        youtube_playlist_id=args.playlist,
        novel_title=args.novel_title,
        youtube_uploader=youtube_uploader,
    )

    print("\n🎉 HOÀN THÀNH PIPELINE!")
    print(f"  • Tổng số chapter: {summary['total_chapters']}")
    print(f"  • Đã render mới:   {summary['processed']}")
    print(f"  • Đã bỏ qua (xong):{summary['skipped']}")
    print(f"  • Đã đăng YouTube: {summary.get('uploaded', 0)}")
    print(f"  • Thất bại:       {summary['failed']}")
    print(f"  • Thư mục MP4:    {summary['output_dir']}")


if __name__ == "__main__":
    main()
