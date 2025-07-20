import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher_string.dart';
import 'scanner.dart';

class GuestPage extends StatelessWidget {
  const GuestPage({super.key});

  @override
  Widget build(context) {
    final border = RoundedRectangleBorder(
      borderRadius: BorderRadius.circular(5),
    );

    return Material(
      child: SafeArea(
        child: Padding(
          padding: EdgeInsets.symmetric(horizontal: 10),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Expanded(
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const SizedBox(width: 20),
                    const Text('Diabeat', style: TextStyle(fontSize: 55)),
                    IconButton(
                      onPressed: _launchRepo,
                      iconSize: 55,
                      color: Colors.red,
                      icon: Icon(Icons.bloodtype),
                    ),
                  ],
                ),
              ),
              FilledButton(
                onPressed: () => _navigateScanPage(context),
                style: FilledButton.styleFrom(
                  fixedSize: Size.fromHeight(50),
                  shape: border,
                ),
                child: const Text('登入'),
              ),
              const SizedBox(height: 10),
              OutlinedButton(
                onPressed: () => _navigateScanPage(context),
                style: OutlinedButton.styleFrom(
                  fixedSize: Size.fromHeight(50),
                  shape: border,
                ),
                child: const Text('註冊'),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _launchRepo() async {
    await launchUrlString('https://github.com/MeDeSciNet/Diabeat-AI-fork');
  }

  Future<void> _navigateScanPage(BuildContext context) async {
    await Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => const ScannerPage()),
    );
  }
}
