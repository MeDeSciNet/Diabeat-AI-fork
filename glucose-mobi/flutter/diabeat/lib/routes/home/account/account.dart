import 'package:diabeat/routes/network/session.dart' as session;
import 'package:diabeat/util.dart' as util;
import 'package:flutter/material.dart';

const _white90 = Color.fromARGB(230, 255, 255, 255);

class AccountPage extends StatefulWidget {
  const AccountPage({super.key});

  @override
  State<AccountPage> createState() => _AccountPageState();
}

class _AccountPageState extends State<AccountPage> {
  /// username : true
  /// email    : false
  bool _usernameOrEmail = true;

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
        actions: [util.scanIconButton(context, true)],
      ),
      body: Padding(
        padding: const EdgeInsets.only(left: 20, right: 20, bottom: 20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Card(
              clipBehavior: Clip.antiAlias,
              child: InkWell(
                onTap: () {
                  Navigator.pushNamed(context, '/predict');
                },
                child: AspectRatio(
                  aspectRatio: 16 / 9,
                  child: Stack(
                    children: [
                      Ink.image(
                        image: const AssetImage('assets/insulin.jpg'),
                        alignment: Alignment.topCenter,
                        fit: BoxFit.cover,
                      ),
                      const Positioned(
                        top: 18,
                        right: 18,
                        child: Text(
                          'AI 糖尿病風險檢測',
                          style: TextStyle(fontSize: 18, color: _white90),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
            const SizedBox(height: 20),
            Card(
              clipBehavior: Clip.antiAlias,
              child: InkWell(
                onTap: () {
                  Navigator.pushNamed(context, '/consult');
                },
                child: AspectRatio(
                  aspectRatio: 16 / 9,
                  child: Stack(
                    children: [
                      Ink.image(
                        image: const AssetImage('assets/health.jpg'),
                        alignment: Alignment.topCenter,
                        fit: BoxFit.cover,
                      ),
                      const Positioned(
                        top: 18,
                        right: 18,
                        child: Text(
                          'AI 健康諮詢',
                          style: TextStyle(fontSize: 18, color: _white90),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
            const Spacer(),
            FilledButton.icon(
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
          ],
        ),
      ),
    );
  }
}
