// language_selector.dart
import 'package:flutter/material.dart';

class LanguageOption {
  final String code;
  final String label;
  const LanguageOption(this.code, this.label);
}

const List<LanguageOption> sourceLanguages = [
  LanguageOption("en", "English"),
  LanguageOption("ja", "日本語"),
];

class LanguageSelector extends StatelessWidget {
  final String sourceLang;
  final ValueChanged<String> onChanged;

  const LanguageSelector({
    super.key,
    required this.sourceLang,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      child: Row(
        children: [
          const Icon(Icons.language, color: Color(0xFF00E676), size: 16),
          const SizedBox(width: 8),
          const Text("Từ:",
              style: TextStyle(color: Colors.white70, fontSize: 12)),
          const SizedBox(width: 4),
          SizedBox(
            width: 110,
            child: DropdownButtonHideUnderline(
              child: DropdownButton<String>(
                value: sourceLang,
                dropdownColor: const Color(0xFF1A1A1A),
                style: const TextStyle(color: Colors.white, fontSize: 12),
                items: sourceLanguages
                    .map((l) => DropdownMenuItem(
                          value: l.code,
                          child: Text(l.label),
                        ))
                    .toList(),
                onChanged: (v) {
                  if (v != null) onChanged(v);
                },
              ),
            ),
          ),
          const SizedBox(width: 8),
          const Text("→",
              style: TextStyle(color: Color(0xFF00E676), fontSize: 14)),
          const SizedBox(width: 8),
          const Text("Tiếng Việt",
              style: TextStyle(color: Color(0xFF00E676), fontSize: 12)),
        ],
      ),
    );
  }
}
