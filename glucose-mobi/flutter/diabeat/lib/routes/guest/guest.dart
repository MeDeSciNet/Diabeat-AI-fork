import 'package:diabeat/util.dart' as util;
import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

class GuestPage extends StatelessWidget {
  const GuestPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Material(
      child: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 10),
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
                      icon: const Icon(Icons.bloodtype),
                    ),
                  ],
                ),
              ),
              FilledButton.icon(
                onPressed: () {
                  Navigator.pushNamed(context, '/guest/login');
                },
                style: util.filledPageButtonStyle(),
                icon: const Icon(Icons.login),
                label: const Text('登入'),
              ),
              const SizedBox(height: 10),
              OutlinedButton.icon(
                onPressed: () {
                  Navigator.pushNamed(context, '/guest/register');
                },
                style: util.outlinedPageButtonStyle(),
                icon: const Icon(Icons.create),
                label: const Text('註冊'),
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _launchRepo() {
    launchUrl(Uri.parse('https://github.com/MeDeSciNet/Diabeat-AI-fork'));
  }
}
