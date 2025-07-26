import 'dart:async';
import 'package:diabeat/util.dart';
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
              FilledButton(
                onPressed: () async {
                  await Navigator.pushNamed(context, '/guest/login');
                },
                style: BtnStyleExt.mainFilled,
                child: const Text('登入'),
              ),
              const SizedBox(height: 10),
              OutlinedButton(
                onPressed: () async {
                  await Navigator.pushNamed(context, '/guest/register');
                },
                style: BtnStyleExt.mainOutlined,
                child: const Text('註冊'),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _launchRepo() async {
    await launchUrl(Uri.parse('https://github.com/MeDeSciNet/Diabeat-AI-fork'));
  }
}
