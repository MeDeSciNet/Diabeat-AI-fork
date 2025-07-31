import 'package:diabeat/routes/connection/request.dart';
import 'package:flutter/material.dart';

class AccountPage extends StatelessWidget {
  const AccountPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: FilledButton(
        onPressed: () {
          Request.deleteSession();
          Navigator.pushReplacementNamed(context, '/guest');
        },
        child: const Text('登出'),
      ),
    );
  }
}
