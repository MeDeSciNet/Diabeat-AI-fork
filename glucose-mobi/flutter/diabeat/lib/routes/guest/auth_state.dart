import 'package:diabeat/routes/network/scanner.dart';
import 'package:diabeat/util.dart' as util;
import 'package:flutter/material.dart';

abstract class AuthState<T extends StatefulWidget> extends State<T> {
  final formKey = GlobalKey<FormState>();

  String? emailErr;
  bool passwordObscured = true;
  bool waiting = false;

  late String email;
  late String password;

  Widget buildEmailField() {
    return TextFormField(
      validator: (value) {
        final regex = RegExp(
          r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
        );

        if (value == null || value.isEmpty) {
          return 'Email 不能為空';
        } else if (!regex.hasMatch(value)) {
          return 'Email 格式不正確';
        } else {
          return null;
        }
      },
      onSaved: (newValue) => email = newValue!,
      forceErrorText: emailErr,
      keyboardType: TextInputType.emailAddress,
      textInputAction: TextInputAction.next,
      decoration: util.inputBorder('Email'),
      onChanged: (value) {
        if (emailErr != null) {
          setState(() => emailErr = null);
        }
      },
    );
  }

  InputDecoration passwordDecoration() {
    return InputDecoration(
      labelText: '密碼',
      border: const OutlineInputBorder(),
      suffixIcon: IconButton(
        onPressed: () {
          setState(() => passwordObscured ^= true);
        },
        icon: passwordObscured
            ? const Icon(Icons.visibility)
            : const Icon(Icons.visibility_off),
      ),
    );
  }

  String? passwordValidator(String? value) {
    if (value == null || value.isEmpty) {
      return '密碼不能為空';
    }

    if (value.length < 6) {
      return '密碼至少需要 6 個字母';
    }

    return null;
  }

  OutlinedButton buildScanButton() {
    return OutlinedButton.icon(
      onPressed: waiting
          ? null
          : () {
              ScannerPage.push(context);
            },
      style: util.outlinedPageButtonStyle(),
      icon: const Icon(Icons.qr_code_scanner),
      label: const Text('連線'),
    );
  }

  FormState get formState => formKey.currentState!;
}
