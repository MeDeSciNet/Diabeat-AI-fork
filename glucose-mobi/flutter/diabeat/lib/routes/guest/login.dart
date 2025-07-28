import 'package:diabeat/routes/connection/prefs.dart';
import 'package:diabeat/routes/connection/request.dart';
import 'package:diabeat/routes/guest/auth_state.dart';
import 'package:diabeat/util.dart';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';

class LoginPage extends StatefulWidget {
  const LoginPage({super.key});

  @override
  AuthState<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends AuthState<LoginPage> {
  @override
  void initState() {
    () async {
      final email = await Prefs.getEmail();
      if (email != null) {
        emailCtrl.text = email;
      }
    }(); // sync call
    super.initState();
  }

  Future<void> _tryLogIn() async {
    setState(() {
      submitted = true;
      validateEmail();
      validatePassword();
    });

    if (emailErr != null || passwordErr != null) return;

    setState(() => waiting = true);

    try {
      await Request.logIn(
        context,
        email: emailCtrl.text,
        password: passwordCtrl.text,
        remeberMe: rememberMe,
      );

      if (!mounted) return;
      Navigator.pop(context);
      await Navigator.pushReplacementNamed(context, '/home');
      //
    } on DioException catch (e) {
      setState(() {
        final errMsg = e.response!.data['non_field_errors'][0];

        if (errMsg == 'Email does not exist.') {
          emailErr = 'Email 不存在';
        } else if (errMsg == 'Incorrect password.') {
          passwordErr = '密碼錯誤';
        }
        waiting = false;
      });
    } on CancelConnectionException {
      setState(() => waiting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          onPressed: () {
            Navigator.pop(context);
          },
          icon: const Icon(Icons.arrow_back_ios_new_rounded),
        ),
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Spacer(flex: 1),
              const Text(
                '歡迎回來 !',
                style: TextStyle(fontSize: 35),
                textAlign: TextAlign.center,
              ),
              const Spacer(flex: 1),
              buildEmailField(),
              const SizedBox(height: 20),
              buildPasswordField(),
              const SizedBox(height: 20),
              buildRememberMeCheckbox(),
              const Spacer(flex: 2),
              FilledButton(
                onPressed: waiting ? null : _tryLogIn,
                style: BtnStyleExt.mainFilled,
                child: const Text('登入'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
