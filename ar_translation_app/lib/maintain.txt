import 'dart:async'; 
import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart'; 
import 'package:permission_handler/permission_handler.dart';

// ── Địa chỉ backend Python ─────────────────────────
// Đổi thành IP máy tính của bạn (xem bằng lệnh ipconfig)
const String API_URL = "http://172.20.10.3:8000";

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final cameras = await availableCameras();
  runApp(MyApp(cameras: cameras));
}

class MyApp extends StatelessWidget {
  final List<CameraDescription> cameras;
  const MyApp({super.key, required this.cameras});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'AR Translation',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.green),
        useMaterial3: true,
      ),
      home: HomeScreen(cameras: cameras),
    );
  }
}

// ══════════════════════════════════════════════════
// MÀN HÌNH CHÍNH
// ══════════════════════════════════════════════════
class HomeScreen extends StatefulWidget {
  final List<CameraDescription> cameras;
  const HomeScreen({super.key, required this.cameras});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  late CameraController _controller;
  bool   _isCameraReady  = false;
  bool   _isProcessing   = false;
  String _statusText     = "Hướng camera vào văn bản cần dịch";
  Image? _resultImage;          // ảnh AR nhận từ API
  List   _translations   = [];  // danh sách bản dịch

  @override
  void initState() {
    super.initState();
    _initCamera();
  }

  // ── Khởi tạo camera ─────────────────────────────
  Future<void> _initCamera() async {
    // Xin quyền camera
    final status = await Permission.camera.request();
    if (!status.isGranted) {
      setState(() => _statusText = "❌ Cần cấp quyền camera!");
      return;
    }

    _controller = CameraController(
      widget.cameras[0],      // camera sau
      ResolutionPreset.high,  // độ phân giải cao
      enableAudio: false,
    );

    await _controller.initialize();
    if (mounted) {
      setState(() => _isCameraReady = true);
    }
  }

  // ── Chụp ảnh & gọi API ──────────────────────────
  Future<void> _captureAndTranslate() async {
    if (!_isCameraReady || _isProcessing) return;

    setState(() {
      _isProcessing = true;
      _statusText   = "⏳ Đang xử lý...";
      _resultImage  = null;
    });

    try {
      // Chụp ảnh
      final XFile photo = await _controller.takePicture();
      final String path = photo.path;

      print("📸 Ảnh chụp tại: $path");

      // ── Gửi lên API ──────────────────────────────
      final uri = Uri.parse(
        '$API_URL/translate-image?source_lang=en&target_lang=vi'
      );

      final request = http.MultipartRequest('POST', uri);

      // Thêm file với đúng content-type
      request.files.add(
        http.MultipartFile(
          'file',
          File(path).readAsBytes().asStream(),
          await File(path).length(),
          filename: 'photo.jpg',
          contentType: MediaType('image', 'jpeg'), // ← thêm dòng này
        ),
      );

      print("📤 Đang gửi lên $API_URL...");

      final streamedResponse = await request.send()
          .timeout(const Duration(seconds: 60));
      final response = await http.Response.fromStream(streamedResponse);

      print("📥 Status code: ${response.statusCode}");

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        if (data['status'] == 'success') {
          final imageBytes = base64Decode(data['image_base64']);
          setState(() {
            _resultImage  = Image.memory(imageBytes, fit: BoxFit.contain);
            _translations = data['translations'];
            _statusText   =
                "✅ Dịch xong ${data['regions_translated']} vùng chữ";
          });
        } else {
          setState(() => _statusText = "⚠️ ${data['message']}");
        }
      } else {
        // In ra chi tiết lỗi để debug
        print("❌ Response body: ${response.body}");
        setState(() =>
            _statusText = "❌ Lỗi server: ${response.statusCode}\n${response.body}");
      }

    } on SocketException {
      setState(() => _statusText =
          "❌ Không kết nối được server!\nKiểm tra IP và server đang chạy.");
    } on TimeoutException {
      setState(() => _statusText =
          "❌ Timeout! Server xử lý quá lâu.\nThử lại với ảnh đơn giản hơn.");
    } catch (e) {
      print("❌ Lỗi chi tiết: $e");
      setState(() => _statusText = "❌ Lỗi: $e");
    } finally {
      setState(() => _isProcessing = false);
    }
  }

  // ── Quay lại chế độ camera ───────────────────────
  void _resetCamera() {
    setState(() {
      _resultImage  = null;
      _translations = [];
      _statusText   = "Hướng camera vào văn bản cần dịch";
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  // ══════════════════════════════════════════════════
  // UI
  // ══════════════════════════════════════════════════
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.green.shade800,
        title: const Text(
          '📷 AR Translation',
          style: TextStyle(color: Colors.white,
                           fontWeight: FontWeight.bold),
        ),
        centerTitle: true,
      ),
      body: Column(
        children: [

          // ── Khung hiển thị camera / ảnh kết quả ──
          Expanded(
            flex: 7,
            child: _resultImage != null
                ? _buildResultView()   // hiện ảnh AR
                : _buildCameraView(),  // hiện camera
          ),

          // ── Status bar ────────────────────────────
          Container(
            width: double.infinity,
            color: Colors.grey.shade900,
            padding: const EdgeInsets.symmetric(
                horizontal: 16, vertical: 8),
            child: Text(
              _statusText,
              style: const TextStyle(color: Colors.white, fontSize: 13),
              textAlign: TextAlign.center,
            ),
          ),

          // ── Danh sách bản dịch ────────────────────
          if (_translations.isNotEmpty)
            Expanded(
              flex: 3,
              child: _buildTranslationList(),
            ),

          // ── Nút bấm ──────────────────────────────
          _buildButtonBar(),
        ],
      ),
    );
  }

  // ── Widget camera preview ────────────────────────
  Widget _buildCameraView() {
    if (!_isCameraReady) {
      return const Center(
        child: CircularProgressIndicator(color: Colors.green),
      );
    }
    return ClipRect(
      child: OverflowBox(
        alignment: Alignment.center,
        child: FittedBox(
          fit: BoxFit.cover,
          child: SizedBox(
            width:  _controller.value.previewSize!.height,
            height: _controller.value.previewSize!.width,
            child:  CameraPreview(_controller),
          ),
        ),
      ),
    );
  }

  // ── Widget hiển thị ảnh AR kết quả ──────────────
  Widget _buildResultView() {
    return Stack(
      children: [
        Center(child: _resultImage!),
        // Nút chụp lại góc trên phải
        Positioned(
          top: 10, right: 10,
          child: ElevatedButton.icon(
            onPressed: _resetCamera,
            icon: const Icon(Icons.camera_alt),
            label: const Text("Chụp lại"),
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.green.shade700,
              foregroundColor: Colors.white,
            ),
          ),
        ),
      ],
    );
  }

  // ── Widget danh sách bản dịch ────────────────────
  Widget _buildTranslationList() {
    return Container(
      color: Colors.grey.shade900,
      child: ListView.separated(
        padding: const EdgeInsets.all(8),
        itemCount: _translations.length,
        separatorBuilder: (_, __) =>
            const Divider(color: Colors.grey, height: 1),
        itemBuilder: (context, index) {
          final t = _translations[index];
          return Padding(
            padding: const EdgeInsets.symmetric(
                horizontal: 12, vertical: 6),
            child: Row(
              children: [
                // Số thứ tự
                CircleAvatar(
                  backgroundColor: Colors.green.shade700,
                  radius: 12,
                  child: Text(
                    '${index + 1}',
                    style: const TextStyle(
                        fontSize: 10, color: Colors.white),
                  ),
                ),
                const SizedBox(width: 8),

                // Cột text — dùng Expanded để tránh tràn
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Text gốc tiếng Anh
                      Text(
                        t['original'] ?? '',
                        style: const TextStyle(
                            color: Colors.grey, fontSize: 11),
                        overflow: TextOverflow.ellipsis,
                        maxLines: 1,
                      ),
                      const SizedBox(height: 2),
                      // Text đã dịch tiếng Việt
                      Text(
                        t['translated'] ?? '',
                        style: const TextStyle(
                            color: Colors.white,
                            fontSize: 13,
                            fontWeight: FontWeight.bold),
                        overflow: TextOverflow.ellipsis,
                        maxLines: 1,
                      ),
                    ],
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  // ── Widget nút bấm ───────────────────────────────
  Widget _buildButtonBar() {
    return Container(
      color: Colors.black,
      padding: const EdgeInsets.symmetric(vertical: 16),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceEvenly,
        children: [
          // Nút dịch
          ElevatedButton.icon(
            onPressed: _isProcessing ? null : _captureAndTranslate,
            icon: _isProcessing
                ? const SizedBox(
                    width: 18, height: 18,
                    child: CircularProgressIndicator(
                        strokeWidth: 2, color: Colors.white))
                : const Icon(Icons.translate),
            label: Text(_isProcessing ? "Đang xử lý..." : "Dịch ngay"),
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.green.shade700,
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(
                  horizontal: 28, vertical: 14),
              textStyle: const TextStyle(
                  fontSize: 16, fontWeight: FontWeight.bold),
            ),
          ),
          // Nút reset
          if (_resultImage != null)
            ElevatedButton.icon(
              onPressed: _resetCamera,
              icon: const Icon(Icons.refresh),
              label: const Text("Chụp lại"),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.grey.shade700,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(
                    horizontal: 20, vertical: 14),
              ),
            ),
        ],
      ),
    );
  }
}