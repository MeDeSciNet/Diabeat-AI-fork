import 'package:diabeat/util.dart';
import 'package:flutter/material.dart';

abstract class AuthState<T extends StatefulWidget> extends State<T> {
  final emailCtrl = TextEditingController();
  final passwordCtrl = TextEditingController();
  String? emailErr;
  String? passwordErr;
  bool _passwordObscured = true;
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

  TextField buildPasswordField() {
    return TextField(
      controller: passwordCtrl,
      keyboardType: TextInputType.visiblePassword,
      textInputAction: TextInputAction.done,
      decoration: InputDecoration(
        labelText: '密碼',
        errorText: passwordErr,
        border: const OutlineInputBorder(),
        suffixIcon: IconButton(
          onPressed: () {
            setState(() => _passwordObscured ^= true);
          },
          icon: _passwordObscured
              ? const Icon(Icons.visibility)
              : const Icon(Icons.visibility_off),
        ),
      ),
      obscureText: _passwordObscured,
      onChanged: (value) {
        if (submitted) {
          setState(validatePassword);
        }
      },
    );
  }

  OutlinedButton buildScanButton() {
    return OutlinedButton(
      onPressed: () {
        Navigator.pushNamed(context, '/connection/scanner');
      },
      style: PageButtons.outlined,
      child: const Icon(Icons.qr_code_scanner),
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
