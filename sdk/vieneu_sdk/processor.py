"""
processor.py — Batch Processor quản lý quét folder, lọc số lượng, checkpoint và hiển thị tiến trình.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from tqdm import tqdm

from vieneu_sdk.client import VieneuClient
from vieneu_sdk.sorter import NaturalSorter


class NovelBatchProcessor:
    """Bộ xử lý hàng loạt chapter truyện phía Client."""

    def __init__(self, client: VieneuClient):
        self.client = client
        self.sorter = NaturalSorter()

    def scan_and_filter(
        self,
        folder_path: Path,
        pattern: str = "*.txt",
        start_chapter: Optional[int] = None,
        end_chapter: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> List[Path]:
        """Quét folder, sắp xếp tự nhiên và áp dụng bộ lọc số lượng."""
        if not folder_path.exists() or not folder_path.is_dir():
            raise FileNotFoundError(f"Thư mục truyện không tồn tại: {folder_path}")

        files = list(folder_path.glob(pattern))
        sorted_files = self.sorter.sort_files(files)

        filtered = []
        for file_p in sorted_files:
            chap_num = self.sorter.extract_chapter_number(file_p.name)

            if start_chapter is not None and chap_num < start_chapter:
                continue
            if end_chapter is not None and chap_num > end_chapter:
                continue

            filtered.append(file_p)

            if limit is not None and len(filtered) >= limit:
                break

        return filtered

    def process(
        self,
        folder_path: Path,
        cover_path: Path,
        output_dir: Path,
        voice: str = "Ngọc Huyền",
        speed: float = 1.2,
        pattern: str = "*.txt",
        start_chapter: Optional[int] = None,
        end_chapter: Optional[int] = None,
        limit: Optional[int] = None,
        resume: bool = True,
        auto_upload_youtube: bool = False,
        youtube_privacy: str = "unlisted",
        youtube_playlist_id: Optional[str] = None,
        novel_title: str = "Tiểu Thuyết",
        youtube_uploader: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Chạy pipeline render video hàng loạt cho danh sách chapter."""
        chapters = self.scan_and_filter(
            folder_path=folder_path,
            pattern=pattern,
            start_chapter=start_chapter,
            end_chapter=end_chapter,
            limit=limit,
        )

        if not chapters:
            print("⚠️ Không tìm thấy file chapter nào khớp với điều kiện lọc.")
            return {"processed": 0, "skipped": 0, "failed": 0}

        output_dir.mkdir(parents=True, exist_ok=True)
        checkpoint_file = output_dir / ".batch_checkpoint.json"

        completed_set = set()
        checkpoint_data: Dict[str, Any] = {}
        if resume and checkpoint_file.exists():
            try:
                raw_data = json.loads(checkpoint_file.read_text("utf-8"))
                if isinstance(raw_data, list):
                    completed_set = set(raw_data)
                elif isinstance(raw_data, dict):
                    checkpoint_data = raw_data
                    completed_set = set(raw_data.keys())
            except Exception:
                completed_set = set()

        processed_count = 0
        skipped_count = 0
        failed_count = 0
        uploaded_count = 0

        with self.client.gpu_session(voice_preload=[voice]):
            pbar = tqdm(chapters, desc="🎬 Render Novel Videos", unit="chap")

            for chap_file in pbar:
                chap_name = chap_file.stem
                out_mp4 = output_dir / f"{chap_name}.mp4"

                pbar.set_postfix({"chapter": chap_name})

                if resume and (chap_name in completed_set or out_mp4.exists()):
                    skipped_count += 1
                    continue

                try:
                    text_content = chap_file.read_text(encoding="utf-8")
                    self.client.render_chapter_video(
                        chapter_text=text_content,
                        cover_image_path=cover_path,
                        output_file_path=out_mp4,
                        chapter_name=chap_name,
                        voice=voice,
                        speed=speed,
                    )

                    yt_result_info = {}
                    if auto_upload_youtube and youtube_uploader:
                        chap_num = self.sorter.extract_chapter_number(chap_file.name)
                        from vieneu_sdk.youtube.metadata import NovelMetadataBuilder

                        meta_builder = NovelMetadataBuilder(novel_title=novel_title)
                        metadata = meta_builder.build_for_chapter(
                            chapter_name=chap_name,
                            chapter_number=chap_num,
                            privacy=youtube_privacy,
                            playlist_id=youtube_playlist_id,
                        )
                        res = youtube_uploader.upload_video(
                            video_path=out_mp4,
                            metadata=metadata,
                            thumbnail_path=cover_path,
                        )
                        if res.status == "uploaded":
                            uploaded_count += 1
                            yt_result_info = {
                                "youtube_id": res.video_id,
                                "youtube_url": res.video_url,
                            }

                    completed_set.add(chap_name)
                    checkpoint_data[chap_name] = {
                        "rendered_mp4": str(out_mp4),
                        "status": "completed",
                        **yt_result_info,
                    }
                    checkpoint_file.write_text(
                        json.dumps(checkpoint_data, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
                    processed_count += 1
                except Exception as e:
                    print(f"\n❌ Lỗi khi render chapter {chap_name}: {e}")
                    failed_count += 1

        summary = {
            "total_chapters": len(chapters),
            "processed": processed_count,
            "skipped": skipped_count,
            "failed": failed_count,
            "uploaded": uploaded_count,
            "output_dir": str(output_dir),
        }
        return summary
