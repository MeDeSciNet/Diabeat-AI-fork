import 'package:diabeat/routes/home/account/predict_diabetes/fields.dart';
import 'package:flutter/material.dart';

class Page3 extends StatefulWidget {
  const Page3({super.key});

  @override
  State<Page3> createState() => Page3State();
}

class Page3State extends State<Page3> {
  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text(switch (PredictDiabetesField().prediction) {
          true => '是',
          false => '否',
          _ => '預測中',
        }),
      ],
    );
  }
}
