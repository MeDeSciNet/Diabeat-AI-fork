import 'package:diabeat/routes/network/request.dart' as request;
import 'package:flutter/material.dart';

class ChartPage extends StatefulWidget {
  const ChartPage({super.key});

  @override
  State<ChartPage> createState() => ChartPageState();
}

class ChartPageState extends State<ChartPage> {
  List<Map<String, dynamic>>? data;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Expanded(
          child: ListView.builder(
            itemCount: data?.length,
            itemBuilder: (context, index) {
              if (data == null) return null;

              final item = data![index];
              return Row(
                children: [
                  Expanded(child: Text(item['blood_glucose'].toString())),
                  Expanded(child: Text(item['carbohydrate_intake'].toString())),
                  Expanded(child: Text(item['exercise_duration'].toString())),
                  Expanded(child: Text(item['insulin_injection'].toString())),
                ],
              );
            },
          ),
        ),
        FilledButton(
          onPressed: () async {
            final result = await request.getRecords(context);
            if (!mounted) return;
            setState(() => data = result.data);
          },
          child: const Text('refresh'),
        ),
      ],
    );
  }

  void update() {
    setState(() {});
  }
}
