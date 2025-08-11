import 'package:diabeat/util.dart' as util;
import 'package:flutter/material.dart';
import 'package:share_plus/share_plus.dart';

class Page3 extends StatefulWidget {
  const Page3({super.key});

  @override
  State<Page3> createState() => Page3State();
}

class Page3State extends State<Page3> {
  bool? _prediction;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(_prediction == null ? '預測中' : (_prediction! ? '是' : '否')),
        const Spacer(),
        FilledButton.icon(
          onPressed: () {
            SharePlus.instance.share(ShareParams(text: '123'));
          },
          style: util.filledPageButtonStyle(),
          icon: const Icon(Icons.ios_share),
          label: const Text('分享'),
        ),
      ],
    );
  }

  void update(bool prediction) {
    setState(() => _prediction = prediction);
  }
}
