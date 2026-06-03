import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:image/image.dart' as img_lib;
import 'language_selector.dart';

const String API_URL = "http://192.168.1.8:8000"; // ← đổi IP của bạn

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
      theme: ThemeData.dark().copyWith(
        scaffoldBackgroundColor: const Color(0xFF0A0A0A),
        colorScheme: const ColorScheme.dark(
          primary:   Color(0xFF00E676),
          secondary: Color(0xFF1DE9B6),
          surface:   Color(0xFF1A1A1A),
        ),
      ),
      home: HomeScreen(cameras: cameras),
    );
  }
}

// ══════════════════════════════════════════════════════
// HOME SCREEN
// ══════════════════════════════════════════════════════
class HomeScreen extends StatefulWidget {
  final List<CameraDescription> cameras;
  const HomeScreen({super.key, required this.cameras});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen>
    with TickerProviderStateMixin {

  // ── Camera ──────────────────────────────────────────
  late CameraController _cameraController;
  bool   _isCameraReady  = false;
  bool   _isProcessing   = false;
  String _statusText     = "Hướng camera vào văn bản cần dịch";
  Image? _resultImage;
  List   _translations   = [];

  // ── Ngôn ngữ ──────────────────────────────────────────
  String _sourceLang  = "en";
  String _targetLang  = "vi";

  // ── Animation controllers ───────────────────────────
  late AnimationController _pulseController;
  late AnimationController _fadeController;
  late AnimationController _scanController;
  late Animation<double>   _pulseAnim;
  late Animation<double>   _fadeAnim;
  late Animation<double>   _scanAnim;

  @override
  void initState() {
    super.initState();
    _initAnimations();
    _initCamera();
  }

  void _initAnimations() {
    _pulseController = AnimationController(
      vsync:    this,
      duration: const Duration(milliseconds: 1200),
    )..repeat(reverse: true);
    _pulseAnim = Tween<double>(begin: 1.0, end: 1.08).animate(
      CurvedAnimation(parent: _pulseController,
                      curve: Curves.easeInOut),
    );

    _fadeController = AnimationController(
      vsync:    this,
      duration: const Duration(milliseconds: 600),
    );
    _fadeAnim = CurvedAnimation(
        parent: _fadeController, curve: Curves.easeIn);

    _scanController = AnimationController(
      vsync:    this,
      duration: const Duration(milliseconds: 2000),
    )..repeat(reverse: true);
    _scanAnim = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(parent: _scanController,
                      curve: Curves.easeInOut),
    );
  }

  Future<void> _initCamera() async {
    final status = await Permission.camera.request();
    if (!status.isGranted) {
      setState(() => _statusText = "❌ Cần cấp quyền camera!");
      return;
    }

    _cameraController = CameraController(
      widget.cameras[0],
      ResolutionPreset.high,
      enableAudio: false,
    );

    await _cameraController.initialize();
    if (mounted) setState(() => _isCameraReady = true);
  }

  Future<void> _captureAndTranslate() async {
    if (!_isCameraReady || _isProcessing) return;

    setState(() {
      _isProcessing = true;
      _statusText   = "⏳ Đang xử lý...";
      _resultImage  = null;
      _translations = [];
    });

    _scanController.stop();

    try {
      final XFile photo = await _cameraController.takePicture();

      setState(() => _statusText = "🗜️ Đang nén ảnh...");
      final bytes      = await photo.readAsBytes();
      final original   = img_lib.decodeImage(bytes);
      // Resize mạnh: 720px + quality 60 → ~200KB, gửi nhanh
      final resized    = img_lib.copyResize(original!, width: 720);
      final compressed = img_lib.encodeJpg(resized, quality: 60);

      print("📸 Gốc: ${bytes.length ~/ 1024}KB → "
            "Nén: ${compressed.length ~/ 1024}KB");

      setState(() => _statusText = "🌐 Đang gửi lên server...");

      final uri     = Uri.parse(
          '$API_URL/translate-image?source_lang=$_sourceLang&target_lang=$_targetLang');
      final request = http.MultipartRequest('POST', uri);
      request.files.add(
        http.MultipartFile.fromBytes(
          'file', compressed,
          filename:    'photo.jpg',
          contentType: MediaType('image', 'jpeg'),
        ),
      );

      setState(() => _statusText = "🔍 Đang nhận dạng & dịch...");

      final streamed = await request.send()
          .timeout(const Duration(seconds: 120));
      final response = await http.Response.fromStream(streamed);

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        if (data['status'] == 'success') {
          final imageBytes = base64Decode(data['image_base64']);

          setState(() {
            _resultImage  = Image.memory(imageBytes,
                                         fit: BoxFit.contain);
            _translations = data['translations'];
            _statusText   =
                "✅ Dịch xong ${data['regions_translated']} vùng";
          });

          _fadeController.reset();
          _fadeController.forward();

        } else {
          setState(() => _statusText = "⚠️ ${data['message']}");
          _scanController.repeat(reverse: true);
        }
      } else {
        setState(() =>
            _statusText = "❌ Lỗi server: ${response.statusCode}");
        _scanController.repeat(reverse: true);
      }

    } on SocketException {
      setState(() => _statusText = "❌ Không kết nối được server!");
      _scanController.repeat(reverse: true);
    } on TimeoutException {
      setState(() => _statusText =
          "❌ Timeout! Thử chụp vùng chữ nhỏ hơn.");
      _scanController.repeat(reverse: true);
    } catch (e) {
      setState(() => _statusText = "❌ Lỗi: $e");
      _scanController.repeat(reverse: true);
    } finally {
      setState(() => _isProcessing = false);
    }
  }

  void _resetCamera() {
    setState(() {
      _resultImage  = null;
      _translations = [];
      _statusText   = "Hướng camera vào văn bản cần dịch";
    });
    _fadeController.reset();
    _scanController.repeat(reverse: true);
  }

  @override
  void dispose() {
    _cameraController.dispose();
    _pulseController.dispose();
    _fadeController.dispose();
    _scanController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0A0A0A),
      body: SafeArea(
        child: Column(
          children: [
            _buildAppBar(),
            Expanded(flex: 7, child: _buildMainView()),
            _buildLanguageSelector(),
            _buildStatusBar(),
            if (_translations.isNotEmpty)
              Expanded(flex: 3, child: _buildTranslationList()),
            _buildBottomBar(),
          ],
        ),
      ),
    );
  }

  Widget _buildAppBar() {
    return Container(
      padding: const EdgeInsets.symmetric(
          horizontal: 16, vertical: 12),
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          colors: [Color(0xFF0A0A0A), Color(0xFF1A1A1A)],
          begin: Alignment.topCenter,
          end:   Alignment.bottomCenter,
        ),
        border: Border(
          bottom: BorderSide(color: Color(0xFF00E676), width: 1),
        ),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(6),
            decoration: BoxDecoration(
              color:        const Color(0xFF00E676).withOpacity(0.15),
              borderRadius: BorderRadius.circular(8),
              border:       Border.all(
                  color: const Color(0xFF00E676), width: 1),
            ),
            child: const Icon(Icons.translate,
                color: Color(0xFF00E676), size: 20),
          ),
          const SizedBox(width: 12),

          const Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text("AR Translation",
                style: TextStyle(
                  color:      Colors.white,
                  fontSize:   18,
                  fontWeight: FontWeight.bold,
                  letterSpacing: 1.2,
                ),
              ),
              Text("Dịch văn bản thực tế ảo",
                style: TextStyle(
                    color:    Color(0xFF00E676),
                    fontSize: 11),
              ),
            ],
          ),

          const Spacer(),

          if (_resultImage != null)
            GestureDetector(
              onTap: _resetCamera,
              child: Container(
                padding: const EdgeInsets.symmetric(
                    horizontal: 12, vertical: 6),
                decoration: BoxDecoration(
                  color:        Colors.white.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(20),
                  border:       Border.all(
                      color: Colors.white24, width: 1),
                ),
                child: const Row(
                  children: [
                    Icon(Icons.refresh,
                        color: Colors.white70, size: 14),
                    SizedBox(width: 4),
                    Text("Chụp lại",
                      style: TextStyle(
                          color: Colors.white70, fontSize: 12)),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildMainView() {
    if (_resultImage != null) {
      return FadeTransition(
        opacity: _fadeAnim,
        child: Container(
          color:  Colors.black,
          child:  Center(child: _resultImage!),
        ),
      );
    }
    return _buildCameraView();
  }

  Widget _buildCameraView() {
    if (!_isCameraReady) {
      return const Center(
        child: CircularProgressIndicator(
            color: Color(0xFF00E676)),
      );
    }

    return Stack(
      children: [
        ClipRect(
          child: OverflowBox(
            alignment: Alignment.center,
            child: FittedBox(
              fit:   BoxFit.cover,
              child: SizedBox(
                width:  _cameraController.value.previewSize!.height,
                height: _cameraController.value.previewSize!.width,
                child:  CameraPreview(_cameraController),
              ),
            ),
          ),
        ),

        _buildCornerOverlay(),

        if (!_isProcessing)
          AnimatedBuilder(
            animation: _scanAnim,
            builder:   (context, child) {
              return Positioned(
                top:   _scanAnim.value *
                       (MediaQuery.of(context).size.height * 0.5),
                left:  0,
                right: 0,
                child: Container(
                  height: 2,
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      colors: [
                        Colors.transparent,
                        const Color(0xFF00E676).withOpacity(0.8),
                        Colors.transparent,
                      ],
                    ),
                  ),
                ),
              );
            },
          ),

        if (_isProcessing)
          Container(
            color: Colors.black54,
            child: Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const CircularProgressIndicator(
                      color: Color(0xFF00E676)),
                  const SizedBox(height: 16),
                  Text(
                    _statusText,
                    style: const TextStyle(
                        color: Color(0xFF00E676), fontSize: 14),
                  ),
                ],
              ),
            ),
          ),
      ],
    );
  }

  Widget _buildCornerOverlay() {
    const color     = Color(0xFF00E676);
    const thickness = 3.0;
    const length    = 24.0;

    return Positioned.fill(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Stack(
          children: [
            Positioned(top: 0, left: 0,
              child: _corner(color, thickness, length,
                  top: true, left: true)),
            Positioned(top: 0, right: 0,
              child: _corner(color, thickness, length,
                  top: true, left: false)),
            Positioned(bottom: 0, left: 0,
              child: _corner(color, thickness, length,
                  top: false, left: true)),
            Positioned(bottom: 0, right: 0,
              child: _corner(color, thickness, length,
                  top: false, left: false)),
          ],
        ),
      ),
    );
  }

  Widget _corner(Color color, double t, double l,
                 {required bool top, required bool left}) {
    return SizedBox(
      width: l, height: l,
      child: CustomPaint(
        painter: _CornerPainter(
            color: color, thickness: t,
            top: top, left: left),
      ),
    );
  }

  // ── Language selector ───────────────────────────────
  Widget _buildLanguageSelector() {
    return LanguageSelector(
      sourceLang: _sourceLang,
      onChanged: (code) => setState(() => _sourceLang = code),
    );
  }

  // ── Status bar ───────────────────────────────────────
  Widget _buildStatusBar() {
    final isError   = _statusText.startsWith("❌");
    final isSuccess = _statusText.startsWith("✅");

    return AnimatedContainer(
      duration: const Duration(milliseconds: 300),
      width:    double.infinity,
      padding:  const EdgeInsets.symmetric(
          horizontal: 16, vertical: 8),
      color: isError
          ? Colors.red.shade900.withOpacity(0.5)
          : isSuccess
              ? const Color(0xFF00E676).withOpacity(0.1)
              : const Color(0xFF1A1A1A),
      child: Text(
        _statusText,
        style: TextStyle(
          color: isError
              ? Colors.red.shade300
              : isSuccess
                  ? const Color(0xFF00E676)
                  : Colors.white70,
          fontSize: 13,
        ),
        textAlign: TextAlign.center,
      ),
    );
  }

  // ── Danh sách bản dịch ──────────────────────────────
  Widget _buildTranslationList() {
    return Container(
      decoration: const BoxDecoration(
        color: Color(0xFF111111),
        border: Border(
          top: BorderSide(color: Color(0xFF00E676), width: 1),
        ),
      ),
      child: Column(
        children: [
          // Header
          Padding(
            padding: const EdgeInsets.symmetric(
                horizontal: 16, vertical: 8),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text("KẾT QUẢ DỊCH",
                  style: TextStyle(
                    color:      Color(0xFF00E676),
                    fontSize:   12,
                    fontWeight: FontWeight.bold,
                    letterSpacing: 1.2,
                  ),
                ),
                Text("${_translations.length} vùng",
                  style: const TextStyle(
                      color: Colors.white38, fontSize: 11),
                ),
              ],
            ),
          ),
          const Divider(height: 1, color: Color(0xFF333333)),

          // Danh sách
          Expanded(
            child: ListView.separated(
              padding: const EdgeInsets.all(8),
              itemCount: _translations.length,
              separatorBuilder: (_, __) => const SizedBox(height: 4),
              itemBuilder: (context, index) {
                final t = _translations[index];
                return Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color:       const Color(0xFF1A1A1A),
                    borderRadius: BorderRadius.circular(6),
                    border:      Border.all(
                        color: Colors.white12, width: 0.5),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Original
                      Text(t['original'] ?? '',
                        style: const TextStyle(
                          color:     Colors.white54,
                          fontSize:  12,
                          decoration:
                              TextDecoration.lineThrough,
                        ),
                      ),
                      const SizedBox(height: 2),
                      // Translated
                      Text(t['translated'] ?? '',
                        style: const TextStyle(
                          color:     Colors.white,
                          fontSize:  14,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ],
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  // ── Bottom bar ──────────────────────────────────────
  Widget _buildBottomBar() {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 12),
      decoration: const BoxDecoration(
        border: Border(
          top: BorderSide(color: Color(0xFF1A1A1A), width: 1),
        ),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          ScaleTransition(
            scale: _isProcessing
                ? const AlwaysStoppedAnimation(1.0)
                : _pulseAnim,
            child: GestureDetector(
              onTap: _isProcessing ? null : _captureAndTranslate,
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 300),
                width:  72,
                height: 72,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: _isProcessing
                      ? Colors.grey.shade800
                      : const Color(0xFF00E676),
                  boxShadow: _isProcessing
                      ? []
                      : [
                          BoxShadow(
                            color:      const Color(0xFF00E676)
                                .withOpacity(0.4),
                            blurRadius: 20,
                            spreadRadius: 4,
                          ),
                        ],
                ),
                child: _isProcessing
                    ? const Center(
                        child: SizedBox(
                          width:  28, height: 28,
                          child:  CircularProgressIndicator(
                            color:       Colors.white,
                            strokeWidth: 2.5,
                          ),
                        ),
                      )
                    : const Icon(Icons.translate,
                        color: Colors.black, size: 32),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ══════════════════════════════════════════════════════
// CUSTOM PAINTER
// ══════════════════════════════════════════════════════
class _CornerPainter extends CustomPainter {
  final Color  color;
  final double thickness;
  final bool   top;
  final bool   left;

  _CornerPainter({
    required this.color,
    required this.thickness,
    required this.top,
    required this.left,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color       = color
      ..strokeWidth = thickness
      ..style       = PaintingStyle.stroke
      ..strokeCap   = StrokeCap.square;

    final path = Path();
    final w = size.width;
    final h = size.height;

    if (top && left) {
      path.moveTo(0, h);
      path.lineTo(0, 0);
      path.lineTo(w, 0);
    } else if (top && !left) {
      path.moveTo(0, 0);
      path.lineTo(w, 0);
      path.lineTo(w, h);
    } else if (!top && left) {
      path.moveTo(0, 0);
      path.lineTo(0, h);
      path.lineTo(w, h);
    } else {
      path.moveTo(w, 0);
      path.lineTo(w, h);
      path.lineTo(0, h);
    }

    canvas.drawPath(path, paint);
  }

  @override
  bool shouldRepaint(_CornerPainter old) => false;
}
