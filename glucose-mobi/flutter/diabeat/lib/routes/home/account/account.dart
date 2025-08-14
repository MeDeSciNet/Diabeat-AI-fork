import 'package:diabeat/routes/network/session.dart' as session;
import 'package:diabeat/util.dart' as util;
import 'package:flutter/material.dart';

class AccountPage extends StatefulWidget {
  const AccountPage({super.key});

  @override
  State<AccountPage> createState() => AccountPageState();
}

class AccountPageState extends State<AccountPage> {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        leading: const Icon(Icons.account_circle_rounded),
        title: session.loggedIn ? Text(session.username) : null,
        actions: [util.scanButton(context)],
      ),
      body: Padding(
        padding: EdgeInsets.all(20),
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
                        image: const AssetImage('assets/images/insulin.jpg'),
                        alignment: Alignment.topCenter,
                        fit: BoxFit.cover,
                      ),
                      const Positioned(
                        top: 18,
                        right: 18,
                        child: Text(
                          'AI 糖尿病風險檢測',
                          style: TextStyle(fontSize: 18),
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
                  Navigator.pushNamed(context, '/chat');
                },
                child: AspectRatio(
                  aspectRatio: 16 / 9,
                  child: Stack(
                    children: [
                      Ink.image(
                        image: const AssetImage('assets/images/health.jpg'),
                        alignment: Alignment.topCenter,
                        fit: BoxFit.cover,
                      ),
                      const Positioned(
                        top: 18,
                        right: 18,
                        child: Text('AI 健康諮詢', style: TextStyle(fontSize: 18)),
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
