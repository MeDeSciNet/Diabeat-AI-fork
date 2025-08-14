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
                      onPressed: () {
                        launchUrl(
                          Uri.parse(
                            'https://github.com/MeDeSciNet/Diabeat-AI-fork',
                          ),
                        );
                      },
                      iconSize: 55,
                      color: Colors.red,
                      icon: const Icon(Icons.bloodtype_rounded),
                    ),
                  ],
                ),
              ),
              FilledButton.icon(
                onPressed: () {
                  Navigator.of(context).pushNamed('/guest/login');
                },
                style: util.filledPageButtonStyle(),
                icon: const Icon(Icons.login_rounded),
                label: const Text('登入'),
              ),
              const SizedBox(height: 10),
              OutlinedButton.icon(
                onPressed: () {
                  Navigator.of(context).pushNamed('/guest/register');
                },
                style: util.outlinedPageButtonStyle(),
                icon: const Icon(Icons.create_rounded),
                label: const Text('註冊'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
