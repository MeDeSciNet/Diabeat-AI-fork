import 'package:diabeat/routes/network/session.dart' as session;
import 'package:diabeat/util.dart' as util;
import 'package:flutter/material.dart';

class AccountPage extends StatefulWidget {
  const AccountPage({super.key});

  @override
  State<AccountPage> createState() => _AccountPageState();
}

class _AccountPageState extends State<AccountPage> {
  @override
  void initState() {
    () async {
      await session.tryAuthorize(context);
      setState(() {});
    }();
    super.initState();
  }

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
              'Hello, ${session.loggedIn ? session.username : ''}',
              style: const TextStyle(fontSize: 55),
              textAlign: TextAlign.center,
            ),
            const Spacer(),
            OutlinedButton(
              onPressed: () {
                Navigator.pushNamed(context, '/account/predict_diabetes');
              },
              child: const Text('預測糖尿病'),
            ),
            const Spacer(),
            FilledButton.icon(
              onPressed: () {
                session.delete();
                Navigator.pushReplacementNamed(context, '/guest');
              },
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
