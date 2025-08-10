import 'package:diabeat/routes/network/connection.dart' as connection;
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
              style: const TextStyle(fontSize: 50),
              textAlign: TextAlign.center,
            ),
            const Spacer(),
            OutlinedButton.icon(
              onPressed: () {
                Navigator.pushNamed(context, '/predict');
              },
              style: util.outlinedPageButtonStyle(),
              icon: const Icon(Icons.auto_awesome),
              label: const Text('預測糖尿病'),
            ),
            const SizedBox(height: 10),
            OutlinedButton.icon(
              onPressed: () async {
                final nav = await Navigator.of(
                  context,
                  rootNavigator: true,
                ).pushNamed('/scanner');

                if (nav == true) {
                  setState(() {});
                }
              },
              style: util.outlinedPageButtonStyle(),
              icon: const Icon(Icons.qr_code_scanner),
              label: Text(connection.existAddr ? connection.addr : '連接'),
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
              icon: const Icon(Icons.logout),
              label: const Text('登出'),
            ),
            const SizedBox(height: 10),
          ],
        ),
      ),
    );
  }
}
