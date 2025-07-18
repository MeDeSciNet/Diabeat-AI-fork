import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher_string.dart';

class WelcomePage extends StatelessWidget {
  const WelcomePage({super.key});

  @override
  Widget build(context) {
    final border = RoundedRectangleBorder(
      borderRadius: BorderRadius.circular(5),
    );

    return Padding(
      padding: EdgeInsets.symmetric(horizontal: 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Expanded(
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                SizedBox(width: 20),
                Text('Diabeat', style: TextStyle(fontSize: 55)),
                IconButton(
                  onPressed: _launchRepo,
                  iconSize: 55,
                  color: Colors.red,
                  icon: Icon(Icons.bloodtype),
                ),
              ],
            ),
          ),
          FilledButton(
            onPressed: () {},
            style: FilledButton.styleFrom(
              fixedSize: Size.fromHeight(50),
              shape: border,
            ),
            child: Text('登入'),
          ),
          SizedBox(height: 10),
          OutlinedButton(
            onPressed: () {},
            style: OutlinedButton.styleFrom(
              fixedSize: Size.fromHeight(50),
              shape: border,
            ),
            child: Text('註冊'),
          ),
        ],
      ),
    );
  }

  Future<void> _launchRepo() async {
    await launchUrlString('https://github.com/MeDeSciNet/Diabeat-AI-fork');
  }
}
