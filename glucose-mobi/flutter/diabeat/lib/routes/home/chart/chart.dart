import 'dart:developer';

import 'package:diabeat/routes/network/request.dart' as request;
import 'package:flutter/material.dart';

class ChartPage extends StatelessWidget {
  const ChartPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: FilledButton(
        onPressed: () async {
          final result = await request.getRecords(context);
          final data = result.dataAsList;

          for (var element in data) {
            log(element['blood_glucose'].toString());
            log(element['carbohydrate_intake'].toString());
            log(element['exercise_duration'].toString());
            log(element['insulin_injection'].toString());
            log('=====');
          }
        },
        child: Text('Chart'),
      ),
    );
  }
}
