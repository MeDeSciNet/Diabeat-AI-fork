import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher_string.dart';
import '../util.dart';
import '../account/login.dart';

class GuestPage extends StatelessWidget {
  const GuestPage({super.key});

  @override
  Widget build(context) => Material(
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
              onPressed: () {
                navigate(context, (_) => const LoginPage());
              },
              style: BtnStyleExt.mainFilled,
              child: const Text('登入'),
            ),
            const SizedBox(height: 10),
            OutlinedButton(
              onPressed: () {
                navigate(context, (_) => const LoginPage());
              },
              style: BtnStyleExt.mainOutlined,
              child: const Text('註冊'),
            ),
          ],
        ),
      ),
    ),
  );

  Future<void> _launchRepo() async {
    await launchUrlString('https://github.com/MeDeSciNet/Diabeat-AI-fork');
  }
}
