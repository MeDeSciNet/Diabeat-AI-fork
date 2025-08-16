import 'package:flutter/material.dart';

class Page3 extends StatefulWidget {
  const Page3({super.key});

  @override
  State<Page3> createState() => Page3State();
}

class Page3State extends State<Page3> {
  bool? prediction;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text(prediction == null ? '預測中' : (prediction! ? '是' : '否')),
      ],
    );
  }

  void update(bool prediction) {
    setState(() => this.prediction = prediction);
  }
}
