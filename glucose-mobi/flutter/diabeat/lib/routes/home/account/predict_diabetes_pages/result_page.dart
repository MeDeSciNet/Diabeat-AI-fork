import 'package:diabeat/util.dart' as util;
import 'package:flutter/material.dart';
import 'package:share_plus/share_plus.dart';

class ResultPage extends StatefulWidget {
  const ResultPage({super.key});

  @override
  State<ResultPage> createState() => ResultPageState();
}

class ResultPageState extends State<ResultPage> {
  bool? prediction;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(prediction == null ? '預測中' : (prediction! ? '是' : '否')),
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
}
