import 'package:diabeat/routes/network/session.dart' as session;
import 'package:flutter/material.dart';

class AccountPage extends StatelessWidget {
  const AccountPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: FilledButton(
        onPressed: () {
          session.delete();
          Navigator.pushReplacementNamed(context, '/guest');
        },
        child: const Text('登出'),
      ),
    );
  }
}
