import 'package:diabeat/routes/guest/login.dart';
import 'package:diabeat/routes/guest/register.dart';
import 'package:diabeat/util.dart' as util;
import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

class GuestPage extends StatefulWidget {
  const GuestPage({super.key});

  @override
  State<GuestPage> createState() => _GuestPageState();
}

class _GuestPageState extends State<GuestPage> {
  final _medescinetImageProvider = const ExactAssetImage(
    'assets/medescinet.png',
    scale: 4,
  );

  /// app name : true
  /// org name : false
  bool _appOrOrgName = true;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    precacheImage(_medescinetImageProvider, context);
  }

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
                    InkWell(
                      onTap: () {
                        setState(() => _appOrOrgName ^= true);
                      },
                      child: _appOrOrgName
                          ? const Text(
                              ' Diabeat',
                              style: TextStyle(fontSize: 55),
                            )
                          : const Text(
                              'MeDeSciNet ',
                              style: TextStyle(fontSize: 40),
                            ),
                    ),
                    IconButton(
                      onPressed: _launchUrl,
                      iconSize: 55,
                      color: Colors.red,
                      icon: _appOrOrgName
                          ? const Icon(Icons.bloodtype_rounded)
                          : Image(image: _medescinetImageProvider),
                    ),
                  ],
                ),
              ),
              FilledButton.icon(
                onPressed: _goLogin,
                style: util.filledPageButtonStyle(),
                icon: const Icon(Icons.login_rounded),
                label: const Text('登入'),
              ),
              const SizedBox(height: 10),
              FilledButton.tonalIcon(
                onPressed: _goRegister,
                style: util.tonalPageButtonStyle(context),
                icon: const Icon(Icons.create_rounded),
                label: const Text('註冊'),
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _launchUrl() {
    launchUrl(
      Uri.parse(
        _appOrOrgName
            ? 'https://github.com/MeDeSciNet/Diabeat-AI-fork'
            : 'https://github.com/MeDeSciNet',
      ),
    );
  }

  void _goLogin() {
    Navigator.push(
      context,
      MaterialPageRoute(builder: (context) => const LoginPage()),
    );
  }

  void _goRegister() {
    Navigator.push(
      context,
      MaterialPageRoute(builder: (context) => const RegisterPage()),
    );
  }
}
