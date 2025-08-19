import 'package:diabeat/network/session.dart' as session;
import 'package:diabeat/util.dart' as util;
import 'package:flutter/material.dart';

class AccountPage extends StatefulWidget {
  const AccountPage({super.key});

  @override
  State<AccountPage> createState() => _AccountPageState();
}

class _AccountPageState extends State<AccountPage> {
  final _insulinImage = const AssetImage('assets/insulin.jpg');
  final _healthImage = const AssetImage('assets/health.jpg');

  /// username : true
  /// email    : false
  bool _usernameOrEmail = true;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((timeStamp) {
      precacheImage(_insulinImage, context);
      precacheImage(_healthImage, context);
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          onPressed: () {
            setState(() => _usernameOrEmail ^= true);
          },
          icon: _usernameOrEmail
              ? const Icon(Icons.person)
              : const Icon(Icons.email_rounded),
        ),
        title: Text(_usernameOrEmail ? session.username : session.email),
        actions: [util.scanIconButton(context, waiting: false)],
      ),
      body: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _card(_insulinImage, 'AI 糖尿病風險檢測', '/predict'),
            const SizedBox(height: 20),
            _card(_healthImage, 'AI 健康諮詢', '/consult'),
            const Spacer(),
            Row(
              spacing: 20,
              children: [
                Expanded(
                  child: FilledButton.tonalIcon(
                    onPressed: () {},
                    style: util.tonalPageButtonStyle(context),
                    icon: const Icon(Icons.edit_rounded),
                    label: const Text('個人資料'),
                  ),
                ),
                Expanded(
                  child: FilledButton.icon(
                    onPressed: () {
                      session.delete();
                      Navigator.of(
                        context,
                        rootNavigator: true,
                      ).pushReplacementNamed('/guest');
                    },
                    style: util.filledPageButtonStyle(),
                    icon: const Icon(Icons.logout_rounded),
                    label: const Text('登出'),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _card(ImageProvider image, String label, String route) {
    return Card(
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: () {
          Navigator.pushNamed(context, route);
        },
        child: AspectRatio(
          aspectRatio: 16 / 9,
          child: Stack(
            children: [
              Ink.image(
                image: image,
                alignment: Alignment.topCenter,
                fit: BoxFit.cover,
              ),
              Positioned(
                top: 18,
                right: 18,
                child: Text(
                  label,
                  style: const TextStyle(
                    fontSize: 18,
                    color: Color.fromARGB(230, 255, 255, 255),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
