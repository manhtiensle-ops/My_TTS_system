import time
from vieneu import Vieneu

tts = Vieneu()

text = "Ta, Lý Viễn, chỉ là một sinh viên đại học chỉ muốn sống nhàn giữa thời loạn. Thế nhưng...\nTrong mắt Tào Tháo, ta là một tên khốn ngày nào cũng mong ông ta chết, miệng lưỡi độc địa hơn cả dao, vậy mà thiếu ta thì thật sự không được.\nTrong mắt Hạ Hầu Đôn, ta là người cháu hiền tài, tài hoa nhưng có số phận đáng thương, thất lạc bên ngoài, nhất định phải hết lòng che chở.\nTrong mắt Tào Hồng, ta là Diêm Vương sống keo kiệt hơn cả ông ta, chuyên nhòm ngó kho lương để vét lợi.\nTrong mắt Lưu Bị, ta là kẻ hiểm độc phá hỏng cơ duyên, cướp mất danh tiếng của ông ta, lại còn hiểu mánh khóe nhân nghĩa hơn cả ông ta.\nTrong mắt Điển Vi, ta là người lo cơm nước, không thể để ta bị chúa công chém chết.\nCòn trong mắt chính mình, ta chỉ muốn tan làm! Chỉ muốn tan làm! Chỉ muốn tan làm!\nKhi Hạ Hầu Đôn vỗ mạnh vào vai ta, vẻ mặt đầy yêu thương gọi một tiếng “hiền điệt yên tâm”, còn Tào Tháo ở bên cạnh tức đến mức rút kiếm, ta chợt hiểu ra.\nTam Quốc này hình như mắc bệnh thật rồi!"

start_time = time.time()
audio = tts.infer(text, voice="Ngọc Huyền",speed=1.2)
elapsed_time = time.time() - start_time

tts.save(audio, "output_ngoc_huyen_1x11115.wav")

sample_rate = 48000
audio_duration = len(audio) / sample_rate
rtf = elapsed_time / audio_duration

print(f"Thời gian xử lý: {elapsed_time:.3f}s")
print(f"Thời lượng audio: {audio_duration:.3f}s")
print(f"RTF: {rtf:.4f} ({'nhanh hơn' if rtf < 1 else 'chậm hơn'} real-time {1/rtf:.2f}x)")