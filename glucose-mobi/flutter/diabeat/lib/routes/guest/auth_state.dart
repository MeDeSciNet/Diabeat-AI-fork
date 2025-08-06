import 'package:diabeat/util.dart' as util;
import 'package:flutter/material.dart';

abstract class AuthState<T extends StatefulWidget> extends State<T> {
  final emailCtrl = TextEditingController();
  final passwordCtrl = TextEditingController();
  String? emailErr;
  String? passwordErr;
  bool passwordObscured = true;
  bool submitted = false;
  bool waiting = false;

  @override
  void dispose() {
    emailCtrl.dispose();
    passwordCtrl.dispose();
    super.dispose();
  }

  TextField buildEmailField() {
    return TextField(
      controller: emailCtrl,
      keyboardType: TextInputType.emailAddress,
      textInputAction: TextInputAction.next,
      decoration: InputDecoration(
        labelText: 'Email',
        errorText: emailErr,
        border: const OutlineInputBorder(),
      ),
      onChanged: (value) {
        if (submitted) {
          setState(validateEmail);
        }
      },
    );
  }

  InputDecoration makePasswordDecoration() {
    return InputDecoration(
      labelText: '密碼',
      errorText: passwordErr,
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

  OutlinedButton buildScanButton() {
    return OutlinedButton.icon(
      onPressed: waiting
          ? null
          : () {
              Navigator.pushNamed(context, '/scanner');
            },
      style: util.outlinedPageButtonStyle(),
      icon: const Icon(Icons.qr_code_scanner),
      label: const Text('連線'),
    );
  }

  void validateEmail() {
    final regex = RegExp(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$');
    final email = emailCtrl.text;

    if (email.isEmpty) {
      emailErr = 'Email 不能為空';
    } else if (!regex.hasMatch(email)) {
      emailErr = 'Email 格式不正確';
    } else {
      emailErr = null;
    }
  }

  void validatePassword() {
    final password = passwordCtrl.text;

    if (password.isEmpty) {
      passwordErr = '密碼不能為空';
    } else if (password.length < 6) {
      passwordErr = '密碼至少需要 6 個字母';
    } else {
      passwordErr = null;
    }
  }
}
