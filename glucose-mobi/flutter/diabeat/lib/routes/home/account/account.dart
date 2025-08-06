import 'package:diabeat/routes/network/session.dart' as session;
import 'package:diabeat/util.dart' as util;
import 'package:flutter/material.dart';

class AccountPage extends StatelessWidget {
  const AccountPage({super.key});

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Padding(
        padding: EdgeInsets.symmetric(horizontal: 10),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Spacer(),
            Text(
              session.loggedIn ? 'Hello, ${session.username}' : 'Nah',
              style: const TextStyle(fontSize: 55),
              textAlign: TextAlign.center,
            ),
            const Spacer(),
            FilledButton.icon(
              onPressed: () {},
              style: util.filledPageButtonStyle(),
              icon: const Icon(Icons.logout),
              label: const Text('登出'),
            ),
          ],
        ),
      ),
    );
  }
}
