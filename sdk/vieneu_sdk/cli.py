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
        description="VieNeu Novel-to-Video CLI — Chuyển đổi folder truyện thành MP4 YouTube",
    )

    parser.add_argument(
        "--folder", "-i",
        required=True,
        type=Path,
        help="Thư mục chứa các file text chapter (.txt)",
    )
    parser.add_argument(
        "--cover", "-c",
        required=True,
        type=Path,
        help="Đường dẫn file ảnh bìa tĩnh (JPG/PNG)",
    )
    parser.add_argument(
        "--output", "-o",
        required=True,
        type=Path,
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

    args = parser.parse_args()

    print(f"🚀 Khởi chạy VieNeu Novel-to-Video Pipeline...")
    print(f"  • GPU Server: {args.server}")
    print(f"  • Thư mục input: {args.folder}")
    print(f"  • Ảnh bìa: {args.cover}")
    print(f"  • Output: {args.output}")
    print(f"  • Giọng đọc: {args.voice} (Tốc độ {args.speed}x)\n")

    client = VieneuClient(base_url=args.server)
    try:
        health = client.check_health()
        print(f"✅ Kết nối GPU Server thành công! Status: {health.get('status')}")
    except Exception as e:
        print(f"⚠️ Không thể kết nối tới GPU Server: {e}")

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
    )

    print("\n🎉 HOÀN THÀNH PIPELINE!")
    print(f"  • Tổng số chapter: {summary['total_chapters']}")
    print(f"  • Đã render mới:   {summary['processed']}")
    print(f"  • Đã bỏ qua (xong):{summary['skipped']}")
    print(f"  • Thất bại:       {summary['failed']}")
    print(f"  • Thư mục MP4:    {summary['output_dir']}")


if __name__ == "__main__":
    main()
